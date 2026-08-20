import type { EventItem } from "../types/api";

type StatusVariant = "success" | "danger" | "warning" | "neutral";

const STATUS_LABELS: Record<EventItem["status"], string> = {
  ACTIVE: "Activo",
  UPDATED: "Actualizado",
  CANCELLED: "Cancelado",
  ARCHIVED: "Archivado",
};

const STATUS_VARIANTS: Record<EventItem["status"], StatusVariant> = {
  ACTIVE: "success",
  UPDATED: "warning",
  CANCELLED: "danger",
  ARCHIVED: "danger",
};

export function getEventStatusLabel(status: EventItem["status"]): string {
  return STATUS_LABELS[status];
}

export function getEventStatusClass(status: EventItem["status"]): string {
  return `event-status-badge event-status-badge--${STATUS_VARIANTS[status]}`;
}
