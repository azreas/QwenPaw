import { Button, Dropdown, Checkbox } from "antd";
import { FilterOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

interface SkillFilterDropdownProps {
  tags: string[];
  selectedTags: string[];
  onChange: (tags: string[]) => void;
}

export function SkillFilterDropdown({ tags, selectedTags, onChange }: SkillFilterDropdownProps) {
  const { t } = useTranslation();

  const handleTagChange = (tag: string, checked: boolean) => {
    if (checked) {
      onChange([...selectedTags, tag]);
    } else {
      onChange(selectedTags.filter((t) => t !== tag));
    }
  };

  const handleClearAll = () => {
    onChange([]);
  };

  const menuItems = [
    ...tags.map((tag) => ({
      key: tag,
      label: (
        <Checkbox
          checked={selectedTags.includes(tag)}
          onChange={(e) => handleTagChange(tag, e.target.checked)}
        >
          {tag}
        </Checkbox>
      ),
    })),
    ...(selectedTags.length > 0
      ? [
          {
            key: "divider",
            type: "divider" as const,
          },
          {
            key: "clear",
            label: (
              <Button type="link" size="small" onClick={handleClearAll}>
                {t("skills.clearFilters")}
              </Button>
            ),
          },
        ]
      : []),
  ];

  return (
    <Dropdown menu={{ items: menuItems }} placement="bottomLeft">
      <Button icon={<FilterOutlined />}>
        {t("skills.filterByTags")}
        {selectedTags.length > 0 && ` (${selectedTags.length})`}
      </Button>
    </Dropdown>
  );
}
