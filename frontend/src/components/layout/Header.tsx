import { useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";

export function Header({ title }: { title: string }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
      <h1 className="text-base font-semibold text-gray-800">{title}</h1>
      {user && (
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <span>{user.is_guest ? `Guest (${user.user_id})` : user.email}</span>
          <button
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
            className="rounded-lg border border-gray-300 px-3 py-1 hover:bg-gray-100"
          >
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
