export default function ProjectDetailsPage({ params }: { params: { slug: string } }) {
  return (
    <div className="container mx-auto p-8 space-y-4">
      <h1 className="text-3xl font-bold">Project: {params.slug}</h1>
      <p className="text-slate-500">Overview and validation summary.</p>
    </div>
  );
}
