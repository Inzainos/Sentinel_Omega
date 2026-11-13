import type { Meta, StoryObj } from "@storybook/react";
import { EmptyState } from "./EmptyState";

const meta: Meta<typeof EmptyState> = {
  title: "Base/EmptyState",
  component: EmptyState,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "select", options: ["info", "warning", "search", "loading"] },
  },
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

export const Info: Story = {
  args: {
    title: "Sin datos disponibles",
    description: "El sistema aún no ha generado suficientes ciclos para mostrar esta métrica. Vuelve más tarde.",
    variant: "info",
  },
};

export const Warning: Story = {
  args: {
    title: "Fuente no configurada",
    description: "La telemetría Schumann no está disponible. Verifica la conexión con Tomsk.",
    variant: "warning",
    action: { label: "Configurar fuente", onClick: () => alert("Configurar fuente") },
  },
};

export const Search: Story = {
  args: {
    title: "Sin correlaciones",
    description: "No se encontraron patrones que coincidan con los filtros actuales. Intenta ampliar el rango.",
    variant: "search",
  },
};

export const Loading: Story = {
  args: {
    title: "Cargando datos...",
    description: "Obteniendo telemetría en vivo de los sensores.",
    variant: "loading",
  },
};

export const WithAction: Story = {
  args: {
    title: "Reentrenamiento requerido",
    description: "Los modelos ONNX necesitan reentrenarse con los datos más recientes.",
    variant: "warning",
    action: { label: "Iniciar reentrenamiento", onClick: () => alert("Reentrenamiento iniciado") },
  },
};