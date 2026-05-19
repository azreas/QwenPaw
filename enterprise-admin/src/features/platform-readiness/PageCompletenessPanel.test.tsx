import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import PageCompletenessPanel from "./PageCompletenessPanel"

describe("PageCompletenessPanel", () => {
  it("renders completeness status, gaps and Console exit relation", () => {
    render(<PageCompletenessPanel pageKey="abilities" showInternalDetails />)

    expect(screen.getByText("页面完整性")).toBeInTheDocument()
    expect(screen.getByText("MVP 可用")).toBeInTheDocument()
    expect(screen.getByText("主要缺口")).toBeInTheDocument()
    expect(
      screen.getByText(/能力来源与依赖关系展示仍需继续补足/),
    ).toBeInTheDocument()
    expect(screen.getByText("阶段化能力")).toBeInTheDocument()
    expect(screen.getByText("Console 退出关系")).toBeInTheDocument()
    expect(
      screen.getByText(/重构 \/skills、\/skill-pool、\/tools、\/mcp 和 \/acp/),
    ).toBeInTheDocument()
    expect(screen.getAllByText("能力目录")).toHaveLength(1)
  })

  it("renders nothing for unknown page key", () => {
    const { container } = render(
      <PageCompletenessPanel pageKey="unknown" showInternalDetails />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it("hides internal readiness details from product pages by default", () => {
    const { container } = render(<PageCompletenessPanel pageKey="abilities" />)

    expect(container).toBeEmptyDOMElement()
  })
})
