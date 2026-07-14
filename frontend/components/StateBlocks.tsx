type StateBlockProps = {
  title: string;
  message?: string;
};

export function LoadingState({ title = "Loading" }: Partial<StateBlockProps>) {
  return (
    <div className="state state-loading">
      <div className="spinner" aria-hidden="true" />
      <span>{title}</span>
    </div>
  );
}

export function ErrorState({ title, message }: StateBlockProps) {
  return (
    <div className="state state-error">
      <strong>{title}</strong>
      {message ? <span>{message}</span> : null}
    </div>
  );
}

export function EmptyState({ title, message }: StateBlockProps) {
  return (
    <div className="state state-empty">
      <strong>{title}</strong>
      {message ? <span>{message}</span> : null}
    </div>
  );
}
