export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-slate-200 p-8 shadow-sm dark:border-slate-800">
        <h2 className="text-2xl font-bold text-center">Create Research Account</h2>
        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Display / Citation Name</label>
            <input
              type="text"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              placeholder="Dr. Jane Doe"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email Address</label>
            <input
              type="email"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              placeholder="researcher@institute.org"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-md bg-sky-600 py-2 font-medium text-white hover:bg-sky-500 transition"
          >
            Register Actor
          </button>
        </form>
      </div>
    </div>
  );
}
