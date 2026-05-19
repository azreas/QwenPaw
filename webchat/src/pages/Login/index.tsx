import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button, Divider, Form, Input, message, Modal, Spin } from "antd";
import { LockOutlined, UserOutlined, AppstoreOutlined, QrcodeOutlined } from "@ant-design/icons";
import { authApi, type QrcodeConfigResponse } from "../../api/modules/auth";
import { useUser } from "../../contexts/UserContext";
import { useTheme } from "../../contexts/ThemeContext";
import {
  stripRouterBasename,
  webchatPath,
  webchatRoutePrefix,
} from "../../utils/deployment";

declare global {
  interface Window {
    WwLogin?: (config: {
      id: string;
      appid: string;
      agentid: string;
      redirect_uri: string;
      state: string;
      href?: string;
    }) => void;
  }
}

const WECOM_LOGIN_SCRIPT_SRC =
  "https://rescdn.qqmail.com/node/ww/wwopenmng/js/sso/wwLogin-1.0.0.js";

function loadWecomLoginScript(): Promise<void> {
  if (window.WwLogin) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${WECOM_LOGIN_SCRIPT_SRC}"], script[data-webchat-wecom-login="true"]`
    );
    if (existing) {
      existing.addEventListener(
        "load",
        () => (window.WwLogin ? resolve() : reject(new Error("load failed"))),
        { once: true }
      );
      existing.addEventListener("error", () => reject(new Error("load failed")), {
        once: true,
      });
      window.setTimeout(() => {
        if (window.WwLogin) {
          resolve();
        }
      }, 0);
      window.setTimeout(() => {
        if (!window.WwLogin) {
          reject(new Error("load failed"));
        }
      }, 3000);
      return;
    }

    const script = document.createElement("script");
    script.src = WECOM_LOGIN_SCRIPT_SRC;
    script.async = true;
    script.dataset.webchatWecomLogin = "true";
    script.onload = () => (window.WwLogin ? resolve() : reject(new Error("load failed")));
    script.onerror = () => reject(new Error("load failed"));
    document.body.appendChild(script);
  });
}

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isDark } = useTheme();
  const { setUser } = useUser();
  const [loading, setLoading] = useState(false);
  const [qrcodeLoading, setQrcodeLoading] = useState(false);
  const [callbackLoading, setCallbackLoading] = useState(false);
  const [qrcodeOpen, setQrcodeOpen] = useState(false);
  const [qrcodeConfig, setQrcodeConfig] = useState<QrcodeConfigResponse | null>(null);
  const [ready, setReady] = useState(false);
  const callbackHandled = useRef(false);
  const [form] = Form.useForm();

  const getSafeRedirect = () => {
    const raw = searchParams.get("redirect") || webchatRoutePrefix;
    const normalized = stripRouterBasename(raw);
    return normalized.startsWith("/") && !normalized.startsWith("//")
      ? normalized
      : webchatRoutePrefix;
  };

  useEffect(() => {
    authApi.status().finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (!ready || callbackHandled.current) {
      return;
    }
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    if (!code || !state) {
      return;
    }
    callbackHandled.current = true;
    setCallbackLoading(true);

    authApi
      .loginWithQrcode(code, state)
      .then((res) => {
        setUser({
          userId: res.user_id,
          username: res.username,
          agentId: res.agent_id,
        });
        navigate(getSafeRedirect(), { replace: true });
      })
      .catch((err) => {
        const next = new URLSearchParams(searchParams);
        next.delete("code");
        next.delete("state");
        const suffix = next.toString();
        navigate(`${webchatPath("/login")}${suffix ? `?${suffix}` : ""}`, { replace: true });
        message.error(
          err instanceof Error ? err.message : t("login.qrcodeFailed")
        );
      })
      .finally(() => {
        setCallbackLoading(false);
      });
  }, [navigate, ready, searchParams, setUser, t]);

  useEffect(() => {
    if (!qrcodeOpen || !qrcodeConfig?.enabled) {
      return;
    }
    const { appid, agentid, redirect_uri, state, href } = qrcodeConfig;
    if (!appid || !agentid || !redirect_uri || !state) {
      message.error(t("login.qrcodeUnavailable"));
      return;
    }

    let cancelled = false;
    setQrcodeLoading(true);
    loadWecomLoginScript()
      .then(() => {
        if (cancelled) {
          return;
        }
        const target = document.getElementById("webchat-wecom-qrcode");
        if (target) {
          target.innerHTML = "";
        }
        window.WwLogin?.({
          id: "webchat-wecom-qrcode",
          appid,
          agentid,
          redirect_uri: encodeURIComponent(redirect_uri),
          state,
          href,
        });
      })
      .catch(() => {
        message.error(t("login.qrcodeScriptFailed"));
      })
      .finally(() => {
        if (!cancelled) {
          setQrcodeLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [qrcodeConfig, qrcodeOpen, t]);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await authApi.login(values.username, values.password);
      setUser({
        userId: res.user_id,
        username: res.username,
        agentId: res.agent_id,
      });
      navigate(getSafeRedirect(), { replace: true });
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : t("login.failed")
      );
    } finally {
      setLoading(false);
    }
  };

  const openQrcodeLogin = async () => {
    setQrcodeLoading(true);
    try {
      const config = await authApi.getQrcodeConfig();
      if (!config.enabled) {
        message.warning(t("login.qrcodeUnavailable"));
        return;
      }
      setQrcodeConfig(config);
      setQrcodeOpen(true);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : t("login.qrcodeUnavailable")
      );
    } finally {
      setQrcodeLoading(false);
    }
  };

  if (!ready) {
    return null;
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 8 }}>
            <AppstoreOutlined style={{ fontSize: 64, color: "#FF6B00" }} />
          </div>
          <h2>{t("login.title")}</h2>
        </div>

        {callbackLoading && (
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
            <Spin tip={t("login.qrcodeLoading")} />
          </div>
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: t("login.usernameRequired") }]}
          >
            <Input
              prefix={
                <UserOutlined
                  style={{
                    color: isDark ? "rgba(255,255,255,0.45)" : undefined,
                  }}
                />
              }
              placeholder={t("login.usernamePlaceholder")}
              autoFocus
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: t("login.passwordRequired") }]}
          >
            <Input.Password
              prefix={
                <LockOutlined
                  style={{
                    color: isDark ? "rgba(255,255,255,0.45)" : undefined,
                  }}
                />
              }
              placeholder={t("login.passwordPlaceholder")}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: 44, borderRadius: 8, fontWeight: 500 }}
            >
              {t("login.submit")}
            </Button>
          </Form.Item>
        </Form>

        <Divider plain style={{ margin: "18px 0 14px" }} />
        <Button
          icon={<QrcodeOutlined />}
          loading={qrcodeLoading}
          onClick={openQrcodeLogin}
          block
          style={{ height: 40, borderRadius: 8, fontWeight: 500 }}
        >
          {t("login.qrcodeButton")}
        </Button>
      </div>

      <Modal
        title={t("login.qrcodeTitle")}
        open={qrcodeOpen}
        footer={null}
        width={360}
        centered
        destroyOnHidden
        onCancel={() => setQrcodeOpen(false)}
      >
        <div
          style={{
            minHeight: 320,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          {qrcodeLoading && <Spin />}
          <div
            id="webchat-wecom-qrcode"
            style={{ display: qrcodeLoading ? "none" : "block" }}
          />
        </div>
      </Modal>
    </div>
  );
}
