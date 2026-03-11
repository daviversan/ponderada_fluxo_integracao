import RankedList from "@/components/RankedList";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-50 px-4 py-12 font-sans dark:bg-zinc-950">
      <header className="mb-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Caffeine Ratio
        </h1>
        <p className="mt-2 text-lg text-zinc-500 dark:text-zinc-400">
          Rank products by caffeine per dollar — get the most buzz for your
          buck.
        </p>
      </header>

      <main className="w-full max-w-3xl space-y-6">
        <RankedList />
      </main>
    </div>
  );
}
