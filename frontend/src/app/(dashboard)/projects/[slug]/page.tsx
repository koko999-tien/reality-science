export default async function ProjectDetailsPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return (
    <div className="container mx-auto p-8 space-y-4">
      <h1 className="text-3xl font-bold">Project: {slug}</h1>
      <p className="text-slate-500">Overview and validation summary.</p>
    </div>
  );
}
