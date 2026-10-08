type PlaceholderPageProps = {
  title: string;
  description: string;
};

function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <div className="card shadow-sm">
      <div className="card-body p-4">
        <h1 className="h3">{title}</h1>
        <p className="text-muted mb-0">{description}</p>
      </div>
    </div>
  );
}

export default PlaceholderPage;