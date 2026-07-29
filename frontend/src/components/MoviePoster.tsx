interface Props {
  posterPath: string;
  title: string;
  size?: "sm" | "md" | "lg";
}

export function MoviePoster({ posterPath, title, size = "md" }: Props) {
  if (posterPath) {
    return <img className={`poster poster-${size}`} src={posterPath} alt={title} loading="lazy" />;
  }
  const initials = title
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  return (
    <div className={`poster poster-${size} poster-fallback`} aria-label={title}>
      {initials}
    </div>
  );
}
