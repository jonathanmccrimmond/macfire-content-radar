// Review sync config for the approval calendar.
// Same MacFire Supabase project as the lead dashboard; Content Radar uses its
// own post_status table (see supabase/schema.sql). The anon/publishable key is
// safe to ship in client-side code: it is protected by row-level security.
//
// pexelsKey: free read-only Pexels API key (pexels.com/api/). Powers the
// "Find images" picker in the review calendar. Safe to expose here —
// read-only, free tier, internal tool only.
window.CONTENT_RADAR_SUPABASE = {
  url: "https://vruphucsmzpehybtijja.supabase.co",
  anonKey: "sb_publishable_2ZisTv6fjNDMXzPbLH1RzA_t2g-FlpT",
  pexelsKey: "iDXd9vy7dQNeefpA1l5zxhR1s71VVMIUeQ1CxiiLO7etriqv9mLdv30N",
};
