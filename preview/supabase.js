(function () {
  const config = window.CONTENT_RADAR_SUPABASE || {};
  const url = config.url || "";
  const anonKey = config.anonKey || "";

  // Why can't we build a client? Surfaced to the page so the warning can say
  // what to actually fix, rather than always blaming the config.
  function clientReason() {
    if (!url || !anonKey) return "config-missing";
    if (!window.supabase || typeof window.supabase.createClient !== "function") {
      return "sdk-missing";
    }
    return null;
  }

  function client() {
    if (clientReason()) return null;
    return window.supabase.createClient(url, anonKey);
  }

  window.ContentRadarStatus = {
    async loadStatuses(slugs) {
      const supabase = client();
      if (!supabase) {
        return { ok: true, connected: false, reason: clientReason(), statuses: {} };
      }

      const { data, error } = await supabase
        .from("post_status")
        .select("slug,status")
        .in("slug", slugs);

      if (error) return { ok: false, connected: true, error: error.message };

      const statuses = {};
      for (const row of data || []) {
        statuses[row.slug] = row.status;
      }
      return { ok: true, connected: true, statuses };
    },

    async saveStatus(slug, status) {
      const supabase = client();
      if (!supabase) {
        return { ok: true, connected: false, localOnly: true, reason: clientReason() };
      }

      const { error } = await supabase
        .from("post_status")
        .upsert({
          slug,
          status,
          decided_at: new Date().toISOString(),
          decided_by: "review-page",
        });

      if (error) return { ok: false, connected: true, error: error.message };
      return { ok: true, connected: true };
    },

    async loadImages(slugs) {
      const supabase = client();
      if (!supabase) return { ok: true, connected: false, reason: clientReason(), images: {} };

      const { data, error } = await supabase
        .from("post_image")
        .select("slug,image_url")
        .in("slug", slugs);

      if (error) return { ok: false, connected: true, error: error.message };

      const images = {};
      for (const row of data || []) {
        if (row.image_url) images[row.slug] = row.image_url;
      }
      return { ok: true, connected: true, images };
    },

    async saveImage(slug, imageUrl) {
      const supabase = client();
      if (!supabase) {
        return { ok: true, connected: false, localOnly: true, reason: clientReason() };
      }

      const { error } = await supabase
        .from("post_image")
        .upsert({ slug, image_url: imageUrl, updated_at: new Date().toISOString() });

      if (error) return { ok: false, connected: true, error: error.message };
      return { ok: true, connected: true };
    },
  };
})();
