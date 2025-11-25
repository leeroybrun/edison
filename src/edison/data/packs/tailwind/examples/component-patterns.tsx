export function Badge({ children }: { children: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-100">
      {children}
    </span>
  );
}

