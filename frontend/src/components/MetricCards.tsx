export interface MetricItem {
  label: string;
  value: string | number;
  subtext?: string;
}

interface MetricCardsProps {
  items: MetricItem[];
}

export function MetricCards({ items }: MetricCardsProps) {
  return (
    <div className="metric-grid">
      {items.map((item, idx) => (
        <div key={idx} className="metric-card">
          <span className="metric-card-label">{item.label}</span>
          <span className="metric-card-value">
            {typeof item.value === "number"
              ? item.value.toLocaleString()
              : item.value}
          </span>
          {item.subtext && (
            <span className="metric-card-subtext">{item.subtext}</span>
          )}
        </div>
      ))}
    </div>
  );
}
