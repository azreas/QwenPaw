# -*- coding: utf-8 -*-
"""Webchat user manager: handles user registration, authentication, and agent mapping.

Users are stored in a JSON file with hashed passwords.
Each user is mapped to an agent workspace for isolation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


logger = logging.getLogger(__name__)

TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600


class WebchatUser(BaseModel):
    """Webchat user model."""

    user_id: str
    username: str
    password_hash: str
    password_salt: str
    agent_id: str
    created_at: str
    last_login: Optional[str] = None


class WebchatUserManager:
    """Manages webchat users with file-based storage.

    Features:
    - User registration with password hashing
    - User authentication with JWT-like tokens
    - User-agent mapping for isolation
    - Default agent assignment for new users
    """

    def __init__(self, data_dir: Path):
        """Initialize user manager.

        Args:
            data_dir: Directory for user data storage
        """
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.users_file = self.data_dir / "webchat_users.json"
        self.token_secret_file = self.data_dir / "token_secret.json"
        self._token_secret: Optional[str] = None

    def _load_users(self) -> Dict[str, Any]:
        """Load users from file."""
        if self.users_file.is_file():
            try:
                with open(self.users_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load users file: %s", e)
                return {"users": {}, "user_agent_map": {}}
        return {"users": {}, "user_agent_map": {}}

    def _save_users(self, data: Dict[str, Any]) -> None:
        """Save users to file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_token_secret(self) -> str:
        """Get or create token signing secret."""
        if self._token_secret:
            return self._token_secret

        if self.token_secret_file.is_file():
            try:
                with open(self.token_secret_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._token_secret = data.get("secret", "")
                    if self._token_secret:
                        return self._token_secret
            except (json.JSONDecodeError, OSError):
                pass

        self._token_secret = secrets.token_hex(32)
        self.token_secret_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_secret_file, "w", encoding="utf-8") as f:
            json.dump({"secret": self._token_secret}, f)
        return self._token_secret

    def _hash_password(
        self,
        password: str,
        salt: Optional[str] = None,
    ) -> tuple[str, str]:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return h, salt

    def _verify_password(
        self,
        password: str,
        stored_hash: str,
        salt: str,
    ) -> bool:
        """Verify password against stored hash."""
        h, _ = self._hash_password(password, salt)
        return hmac.compare_digest(h, stored_hash)

    def _create_token(self, user_id: str) -> str:
        """Create a signed token for user."""
        import base64

        secret = self._get_token_secret()
        payload = json.dumps(
            {
                "sub": user_id,
                "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
                "iat": int(time.time()),
            },
        )
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
        sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload_b64}.{sig}"

    def _verify_token(self, token: str) -> Optional[str]:
        """Verify token and return user_id if valid."""
        import base64

        try:
            parts = token.split(".", 1)
            if len(parts) != 2:
                logger.debug("Token format invalid: expected 2 parts")
                return None
            payload_b64, sig = parts
            secret = self._get_token_secret()
            expected_sig = hmac.new(
                secret.encode(),
                payload_b64.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                logger.debug("Token signature mismatch")
                return None
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            if payload.get("exp", 0) < time.time():
                logger.debug("Token expired")
                return None
            user_id = payload.get("sub")
            logger.debug("Token verified for user: %s", user_id)
            return user_id
        except Exception as exc:
            logger.error("Token verification failed: %s", exc)
            return None

    def register_user(
        self,
        username: str,
        password: str,
        default_agent_id: str = "default",
        create_agent: bool = True,
    ) -> Optional[tuple[str, str]]:
        """Register a new user.

        Args:
            username: Username
            password: Password
            default_agent_id: Default agent ID for the user
            create_agent: Whether to create a new agent for the user

        Returns:
            Tuple of (user_id, token) if successful, None if user exists
        """
        data = self._load_users()

        for user_id, user_data in data["users"].items():
            if user_data.get("username") == username:
                logger.warning("User already exists: %s", username)
                return None

        user_id = f"webchat_{secrets.token_hex(8)}"
        pw_hash, salt = self._hash_password(password)

        agent_id = default_agent_id
        if create_agent:
            try:
                agent_id = self._create_user_agent(user_id, username)
            except Exception as e:
                logger.warning("Failed to create agent for user %s: %s", username, e)

        data["users"][user_id] = {
            "user_id": user_id,
            "username": username,
            "password_hash": pw_hash,
            "password_salt": salt,
            "agent_id": agent_id,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
        }

        data["user_agent_map"][user_id] = agent_id

        self._save_users(data)
        logger.info("User registered: %s -> agent: %s", username, agent_id)

        token = self._create_token(user_id)
        return user_id, token

    def _create_user_agent(self, user_id: str, username: str) -> str:
        """Create a new agent for the user based on default agent.

        Args:
            user_id: User ID
            username: Username

        Returns:
            Agent ID for the new agent
        """
        from ....config.config import (
            AgentProfileConfig,
            AgentProfileRef,
            ChannelConfig,
            MCPConfig,
            HeartbeatConfig,
            load_agent_config,
            save_agent_config,
            generate_short_agent_id,
        )
        from ....config.utils import load_config, save_config
        from ....constant import WORKING_DIR

        logger.info("Creating agent for user %s (user_id=%s)", username, user_id)

        config = load_config()

        agent_id = f"user_{user_id.replace('webchat_', '')}"
        logger.info("Generated agent_id: %s", agent_id)
        
        if agent_id in config.agents.profiles:
            logger.info("Agent %s already exists in config", agent_id)
            return agent_id

        # 使用 WORKING_DIR/workspaces/{username}-agent 作为工作区路径
        from ....constant import WORKING_DIR
        workspace_dir = Path(WORKING_DIR) / "workspaces" / f"{username}-agent"
        logger.info("Workspace directory: %s", workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        default_agent_config = None
        default_workspace = None
        if "default" in config.agents.profiles:
            try:
                default_agent_config = load_agent_config("default")
                default_ref = config.agents.profiles["default"]
                default_workspace = Path(default_ref.workspace_dir).expanduser()
                logger.info("Loaded default agent config from %s", default_workspace)
            except Exception as e:
                logger.warning("Failed to load default agent config: %s", e)

        # 获取所有可用技能
        all_skill_names = []
        try:
            from ....agents.skill_system.registry import get_builtin_skills_dir
            builtin_skills_dir = get_builtin_skills_dir()
            if builtin_skills_dir.exists():
                all_skill_names = [
                    d.name for d in builtin_skills_dir.iterdir() 
                    if d.is_dir() and not d.name.startswith('_')
                ]
                logger.info("Found %d built-in skills: %s", len(all_skill_names), all_skill_names)
        except Exception as e:
            logger.warning("Failed to get built-in skills: %s", e)

        if default_agent_config:
            agent_config = AgentProfileConfig(
                id=agent_id,
                name=f"{username}的智能体",
                description=f"{username}的个人智能体",
                workspace_dir=str(workspace_dir),
                language=default_agent_config.language or "zh",
                channels=default_agent_config.channels.model_copy()
                if default_agent_config.channels
                else ChannelConfig(),
                mcp=default_agent_config.mcp.model_copy()
                if default_agent_config.mcp
                else MCPConfig(),
                heartbeat=default_agent_config.heartbeat.model_copy()
                if default_agent_config.heartbeat
                else HeartbeatConfig(),
            )
        else:
            agent_config = AgentProfileConfig(
                id=agent_id,
                name=f"{username}的智能体",
                description=f"{username}的个人智能体",
                workspace_dir=str(workspace_dir),
                language="zh",
                channels=ChannelConfig(),
                mcp=MCPConfig(),
                heartbeat=HeartbeatConfig(),
            )

        # 先创建 agent_ref 并保存到主配置
        agent_ref = AgentProfileRef(
            id=agent_id,
            workspace_dir=str(workspace_dir),
            enabled=True,
        )

        config.agents.profiles[agent_id] = agent_ref
        if agent_id not in config.agents.agent_order:
            config.agents.agent_order.append(agent_id)
        
        logger.info("Saving config with agent %s", agent_id)
        save_config(config)
        
        # 确保工作区初始化完成后再保存 agent 配置
        logger.info("Initializing workspace for agent %s", agent_id)
        self._initialize_agent_workspace(
            workspace_dir,
            default_workspace,
            skill_names=all_skill_names,
        )
        
        logger.info("Saving agent config for %s", agent_id)
        save_agent_config(agent_id, agent_config)
        
        # 验证 agent.json 是否创建成功
        agent_json_path = workspace_dir / "agent.json"
        if agent_json_path.exists():
            logger.info("agent.json created successfully at %s", agent_json_path)
        else:
            logger.error("agent.json NOT created at %s", agent_json_path)

        logger.info("Created agent %s for user %s", agent_id, username)
        return agent_id

    def _initialize_agent_workspace(
        self,
        workspace_dir: Path,
        default_workspace: Optional[Path] = None,
        skill_names: Optional[list[str]] = None,
    ) -> None:
        """Initialize agent workspace with default files.

        Args:
            workspace_dir: Path to workspace directory
            default_workspace: Path to default agent workspace for copying
            skill_names: List of skill names to enable (all if None)
        """
        from ....constant import WORKING_DIR
        workspace_dir = Path(workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # 使用与 console 相同的方式创建工作目录
        (workspace_dir / "sessions").mkdir(exist_ok=True)
        (workspace_dir / "memory").mkdir(exist_ok=True)
        
        # 创建 skills 目录
        from ....agents.skill_system.store import get_workspace_skills_dir
        get_workspace_skills_dir(workspace_dir).mkdir(exist_ok=True)

        # 从模板目录复制 markdown 文件（与 console 一致）
        language = "zh"  # 默认使用中文
        md_files_dir = (
            Path(__file__).parent.parent.parent.parent / "agents" / "md_files" / language
        )
        if md_files_dir.exists():
            for md_file in md_files_dir.glob("*.md"):
                target_file = workspace_dir / md_file.name
                if not target_file.exists():
                    try:
                        shutil.copy2(md_file, target_file)
                        logger.debug("Copied template file: %s", md_file.name)
                    except Exception as e:
                        logger.warning("Failed to copy %s: %s", md_file.name, e)
        
        # 如果有默认工作区，也复制文件（作为备用）
        if default_workspace and default_workspace.exists():
            for item in ["PROFILE.md", "MEMORY.md", "QA.md", "AGENTS.md", "SOUL.md"]:
                src = default_workspace / item
                if src.exists():
                    dst = workspace_dir / item
                    if not dst.exists():
                        shutil.copy2(src, dst)
                        logger.debug("Copied %s from default workspace", item)

            default_skills = default_workspace / "skills"
            if default_skills.exists() and default_skills.is_dir():
                for skill_file in default_skills.glob("*"):
                    if skill_file.is_file():
                        dst = workspace_dir / "skills" / skill_file.name
                        if not dst.exists():
                            shutil.copy2(skill_file, dst)
                            logger.debug("Copied skill: %s", skill_file.name)

        # 如果指定了技能名称，安装这些技能到工作区
        if skill_names:
            try:
                from ....agents.skill_system import SkillPoolService
                
                pool_service = SkillPoolService()
                for skill_name in skill_names:
                    try:
                        result = pool_service.download_to_workspace(
                            skill_name=skill_name,
                            workspace_dir=workspace_dir,
                            overwrite=False,
                        )
                        if result.get("success"):
                            logger.debug("Installed skill: %s", skill_name)
                        else:
                            logger.warning(
                                "Failed to install skill %s: %s",
                                skill_name,
                                result.get("reason", "unknown"),
                            )
                    except Exception as e:
                        logger.warning("Failed to install skill %s: %s", skill_name, e)
            except Exception as e:
                logger.warning("Failed to initialize skills: %s", e)

        # 创建 HEARTBEAT.md（如果不存在）
        heartbeat_file = workspace_dir / "HEARTBEAT.md"
        if not heartbeat_file.exists():
            heartbeat_file.write_text(
                "# Heartbeat checklist\n"
                "- 扫描收件箱紧急邮件\n"
                "- 查看未来 2h 的日历\n"
                "- 检查待办是否卡住\n"
                "- 若安静超过 8h，轻量 check-in\n",
                encoding="utf-8",
            )

        # 创建 jobs.json
        jobs_file = workspace_dir / "jobs.json"
        if not jobs_file.exists():
            with open(jobs_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"version": 1, "jobs": []},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        # 创建 chats.json
        chats_file = workspace_dir / "chats.json"
        if not chats_file.exists():
            with open(chats_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"version": 1, "chats": []},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

    def authenticate(
        self,
        username: str,
        password: str,
    ) -> Optional[tuple[str, str]]:
        """Authenticate user.

        Args:
            username: Username
            password: Password

        Returns:
            Tuple of (user_id, token) if successful, None otherwise
        """
        data = self._load_users()

        for user_id, user_data in data["users"].items():
            if user_data.get("username") == username:
                stored_hash = user_data.get("password_hash", "")
                stored_salt = user_data.get("password_salt", "")
                if self._verify_password(password, stored_hash, stored_salt):
                    user_data["last_login"] = datetime.now().isoformat()
                    self._save_users(data)
                    token = self._create_token(user_id)
                    return user_id, token
        return None

    def verify_token(self, token: str) -> Optional[str]:
        """Verify token and return user_id.

        Args:
            token: Token to verify

        Returns:
            user_id if valid, None otherwise
        """
        return self._verify_token(token)

    def get_user(self, user_id: str) -> Optional[WebchatUser]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            WebchatUser if found, None otherwise
        """
        data = self._load_users()
        user_data = data["users"].get(user_id)
        if user_data:
            return WebchatUser(**user_data)
        return None

    def get_user_by_username(self, username: str) -> Optional[WebchatUser]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            WebchatUser if found, None otherwise
        """
        data = self._load_users()
        for user_data in data["users"].values():
            if user_data.get("username") == username:
                return WebchatUser(**user_data)
        return None

    def get_agent_id_for_user(self, user_id: str) -> str:
        """Get agent ID for user.

        If user doesn't have an agent, returns default agent ID.

        Args:
            user_id: User ID

        Returns:
            Agent ID for the user
        """
        data = self._load_users()
        agent_id = data["user_agent_map"].get(user_id)
        if not agent_id:
            agent_id = "default"
            data["user_agent_map"][user_id] = agent_id
            self._save_users(data)
        return agent_id

    def set_agent_for_user(self, user_id: str, agent_id: str) -> bool:
        """Set agent for user.

        Args:
            user_id: User ID
            agent_id: Agent ID to assign

        Returns:
            True if successful, False if user not found
        """
        data = self._load_users()
        if user_id not in data["users"]:
            return False

        data["users"][user_id]["agent_id"] = agent_id
        data["user_agent_map"][user_id] = agent_id
        self._save_users(data)
        logger.info("Agent set for user %s: %s", user_id, agent_id)
        return True

    def list_users(self) -> List[WebchatUser]:
        """List all users.

        Returns:
            List of WebchatUser objects
        """
        data = self._load_users()
        return [WebchatUser(**u) for u in data["users"].values()]

    def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User ID to delete

        Returns:
            True if successful, False if user not found
        """
        data = self._load_users()
        if user_id not in data["users"]:
            return False

        del data["users"][user_id]
        if user_id in data["user_agent_map"]:
            del data["user_agent_map"][user_id]
        self._save_users(data)
        logger.info("User deleted: %s", user_id)
        return True

    def has_users(self) -> bool:
        """Check if any users exist.

        Returns:
            True if users exist, False otherwise
        """
        data = self._load_users()
        return bool(data["users"])
