import type { Preview } from "@storybook/react";
import "../src/index.css";

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: "deep",
      values: [
        { name: "deep", value: "#050607" },
        { name: "panel", value: "#0b0c0d" },
        { name: "card", value: "#111214" },
      ],
    },
    layout: "centered",
  },
  globalTypes: {
    theme: {
      description: "Global theme for components",
      defaultValue: "dark",
      toolbar: {
        title: "Theme",
        icon: "circlehollow",
        items: ["dark"],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (Story) => (
      <div className="min-h-screen bg-bg-deep text-fg-primary p-4" style={{ fontFamily: "var(--font-sans)" }}>
        <Story />
      </div>
    ),
  ],
};

export default preview;