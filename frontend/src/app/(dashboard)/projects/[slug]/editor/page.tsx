export default function EquationEditorPage({ params }: { params: { slug: string } }) {
  return (
    <div className="container mx-auto p-8 space-y-6">
      <h1 className="text-3xl font-bold">Mathematical Model Editor — {params.slug}</h1>
      <p className="text-sm text-slate-500">
        Enter typed AST formulas and dimensional variable constraints.
      </p>
    </div>
  );
}
