/** Original decorative artwork and brand-neutral social glyphs (inline SVG, nothing loaded from third parties). */

export function Clouds({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice" aria-hidden fill="currentColor">
      <g opacity="0.9">
        <ellipse cx="140" cy="90" rx="90" ry="34" />
        <ellipse cx="200" cy="72" rx="60" ry="40" />
        <ellipse cx="90" cy="80" rx="45" ry="28" />
      </g>
      <g opacity="0.8">
        <ellipse cx="1020" cy="140" rx="110" ry="38" />
        <ellipse cx="1090" cy="118" rx="70" ry="46" />
        <ellipse cx="960" cy="126" rx="55" ry="32" />
      </g>
      <g opacity="0.6">
        <ellipse cx="620" cy="60" rx="70" ry="24" />
        <ellipse cx="660" cy="46" rx="44" ry="28" />
      </g>
      <circle cx="1130" cy="420" r="6" opacity="0.7" />
      <circle cx="80" cy="400" r="8" opacity="0.7" />
      <circle cx="520" cy="460" r="5" opacity="0.7" />
    </svg>
  );
}

export function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2a9.9 9.9 0 0 0-8.5 15l-1.4 5 5.1-1.3A10 10 0 1 0 12 2Zm0 18.1c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.1 8.1 0 1 1 12 20.1Zm4.5-6c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2c0 1.3.9 2.5 1 2.7.1.2 1.8 2.8 4.4 3.9 1.6.7 2.3.8 3.1.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.6-.3Z" />
    </svg>
  );
}

export function SocialIcon({ name, className }: { name: "facebook" | "instagram" | "youtube"; className?: string }) {
  if (name === "facebook") {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path d="M14 8h3V4h-3c-2.8 0-4.5 1.7-4.5 4.6V11H7v4h2.5v9h4v-9H17l.5-4h-4V8.8c0-.5.3-.8.5-.8Z" />
      </svg>
    );
  }
  if (name === "instagram") {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
      </svg>
    );
  }
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M22 8.2a3 3 0 0 0-2.1-2.1C18 5.6 12 5.6 12 5.6s-6 0-7.9.5A3 3 0 0 0 2 8.2 31 31 0 0 0 1.6 12 31 31 0 0 0 2 15.8a3 3 0 0 0 2.1 2.1c1.9.5 7.9.5 7.9.5s6 0 7.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .4-3.8 31 31 0 0 0-.4-3.8ZM10 15.1V8.9l5.2 3.1L10 15.1Z" />
    </svg>
  );
}
