"""Helm chart 静态门禁 — 不依赖 helm binary。"""

from pathlib import Path

import yaml


CHART_DIR = Path("deploy/helm/qwenpaw")


def load_values(name: str) -> dict:
    with (CHART_DIR / name).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_chart_files_exist():
    expected = [
        "Chart.yaml",
        "values.yaml",
        "values-dev.yaml",
        "values-staging.yaml",
        "values-prod.yaml",
    ]
    for name in expected:
        assert (CHART_DIR / name).is_file(), name


def test_values_define_external_runtime_contract():
    values = load_values("values.yaml")
    assert values["image"]["repository"]
    assert values["service"]["port"] == 8088
    assert values["env"]["QWENPAW_STORAGE_BACKEND"] in {"sqlite", "postgres"}
    assert "QWENPAW_DATABASE_URL" in values["secretEnv"]
    assert "QWENPAW_WEBCHAT_SESSION_SECRET" in values["secretEnv"]
    assert values["persistence"]["working"]["mountPath"] == "/app/working"
    assert values["persistence"]["secrets"]["mountPath"] == "/app/working.secret"
    assert values["persistence"]["backups"]["mountPath"] == "/app/working.backups"


TEMPLATES_DIR = CHART_DIR / "templates"


def read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def test_template_files_exist():
    expected = [
        "_helpers.tpl",
        "configmap.yaml",
        "secret.yaml",
        "serviceaccount.yaml",
        "deployment.yaml",
        "service.yaml",
        "ingress.yaml",
        "pvc.yaml",
        "NOTES.txt",
    ]
    for name in expected:
        assert (TEMPLATES_DIR / name).is_file(), name


def test_deployment_wires_probes_and_mounts():
    text = read_template("deployment.yaml")
    assert "path: {{ .Values.probes.liveness.path }}" in text
    assert "path: {{ .Values.probes.readiness.path }}" in text
    assert "path: {{ .Values.probes.startup.path }}" in text
    assert "mountPath: {{ .Values.persistence.working.mountPath }}" in text
    # 敏感环境变量通过 envFrom + secretRef 注入
    assert "secretRef:" in text
    assert ".Values.existingSecret" in text


def test_deployment_persistence_fallback_to_emptydir():
    """enabled=false 时 volumes 必须回退到 emptyDir 而非引用不存在的 PVC。"""
    text = read_template("deployment.yaml")
    for name in ("working", "secrets", "backups"):
        # 每个 volume 都有 enabled 条件分支
        assert f"persistence.{name}.enabled" in text
        assert "emptyDir: {}" in text


def test_secret_template_carries_secret_env():
    text = read_template("secret.yaml")
    # secretEnv 通过 range 动态渲染，验证 template 引用了 secretEnv
    assert ".Values.secretEnv" in text
    # 生产推荐 existingSecret，template 应有条件守卫
    assert ".Values.existingSecret" in text


def test_ingress_sets_upload_body_limit():
    text = read_template("ingress.yaml")
    # annotations 通过 range 动态渲染
    assert ".Values.ingress.annotations" in text


def test_deployment_references_service_account():
    """Deployment 必须引用 serviceAccountName，ServiceAccount 模板必须存在。"""
    text = read_template("deployment.yaml")
    assert "qwenpaw.serviceAccountName" in text
    sa = read_template("serviceaccount.yaml")
    assert ".Values.serviceAccount.create" in sa


def test_service_account_helper_exists():
    """_helpers.tpl 必须定义 qwenpaw.serviceAccountName helper。"""
    text = read_template("_helpers.tpl")
    assert "qwenpaw.serviceAccountName" in text


def test_configmap_port_derived_from_service_port():
    """QWENPAW_PORT 必须来自 .Values.service.port，避免端口漂移。"""
    text = read_template("configmap.yaml")
    assert ".Values.service.port" in text
    assert "QWENPAW_PORT" in text


def test_values_env_does_not_hardcode_port():
    """values.yaml 的 env 中不应硬编码 QWENPAW_PORT（由 ConfigMap 模板从 service.port 注入）。"""
    values = load_values("values.yaml")
    assert "QWENPAW_PORT" not in values.get("env", {})


def test_helm_workflow_runs_static_gate():
    workflow = Path(".github/workflows/helm-chart.yml").read_text(encoding="utf-8")
    assert "pytest tests/unit/deploy/test_helm_chart.py -q" in workflow
    assert "helm lint deploy/helm/qwenpaw" in workflow
    # CI 必须覆盖多环境 overlay lint
    assert "values-dev.yaml" in workflow
    assert "values-staging.yaml" in workflow
    assert "values-prod.yaml" in workflow
    # CI 必须有 helm template 渲染门禁
    assert "helm template" in workflow
