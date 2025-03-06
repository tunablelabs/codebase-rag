import Chatpage from '@/components/ui/logic';
import { createClient } from "@/utils/supabase/server";
import { redirect } from "next/navigation";


export default async function MainPage(){

  
  const supabase = await createClient()
    const { data, error } = await supabase.auth.getUser()
    if (!data?.user) {
        redirect('/login')
    }
    console.log('oauth',data.user.email)
    return <Chatpage/>

}
