import { createClient } from "@/utils/supabase/server";

export async function POST(req: Request) {
  const supabase = await createClient();
  await supabase.auth.signOut();
  return new Response(null, { status: 200 });
}   