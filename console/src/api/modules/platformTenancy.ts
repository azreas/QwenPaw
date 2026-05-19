import { request } from "../request";
import type {
  DeleteResponse,
  PolicyListResponse,
  TenantListResponse,
  TenantPolicy,
  TenantTemplate,
  TemplateListResponse,
} from "../types/platformTenancy";

const basePath = "/platform/tenancy";

function encoded(value: string): string {
  return encodeURIComponent(value);
}

export const platformTenancyApi = {
  listTenants: () => request<TenantListResponse>(`${basePath}/tenants`),

  listPolicies: () => request<PolicyListResponse>(`${basePath}/policies`),

  savePolicy: (policy: TenantPolicy) =>
    request<TenantPolicy>(`${basePath}/policies/${encoded(policy.policy_id)}`, {
      method: "PUT",
      body: JSON.stringify(policy),
    }),

  deletePolicy: (policyId: string) =>
    request<DeleteResponse>(`${basePath}/policies/${encoded(policyId)}`, {
      method: "DELETE",
    }),

  listTemplates: () => request<TemplateListResponse>(`${basePath}/templates`),

  saveTemplate: (template: TenantTemplate) =>
    request<TenantTemplate>(
      `${basePath}/templates/${encoded(template.template_id)}`,
      {
        method: "PUT",
        body: JSON.stringify(template),
      },
    ),

  deleteTemplate: (templateId: string) =>
    request<DeleteResponse>(`${basePath}/templates/${encoded(templateId)}`, {
      method: "DELETE",
    }),
};
