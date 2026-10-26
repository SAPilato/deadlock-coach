// Read-aloud via the browser's Web Speech API.

export const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

export function speak(text: string, onEnd?: () => void): void {
  if (!canSpeak) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.95;
  if (onEnd) u.onend = onEnd;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking(): void {
  if (canSpeak) window.speechSynthesis.cancel();
}
