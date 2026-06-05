export function getTimeOfDay(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "morning";
  if (hour >= 12 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 22) return "evening";
  return "night";
}

export function buildEmptyStateGreeting(addressAs: string): string {
  const time = getTimeOfDay();
  return `Good ${time}, ${addressAs}. How may I assist you?`;
}
