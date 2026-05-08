local ADDON_NAME, ns = ...

-- Este archivo será sustituido por tools/rss_to_news.py en la pipeline.
-- Mantiene un schema estable para proteger compatibilidad con SavedVariables.
ns.NewsGeneratedAt = 1760000000
ns.NewsSource = "mock"

ns.News = {
    {
        id = "mock-001",
        slug = "consigue-blasones-del-alba-de-heroe",
        title = "Consigue blasones del alba de héroe para mejorar tu equipo gracias a los Lugares del Ritual",
        excerpt = "¡Te contamos cómo realizarlo!",
        author = "Pixpo",
        publishedAt = 1760000000,
        categories = { "Retail", "Midnight" },
        url = "https://altertime.es/consigue-blasones-del-alba-de-heroe-para-mejorar-tu-equipo-gracias-a-los-lugares-del-ritual",
        cover = nil,
        body = {
            { type = "paragraph", text = "Tanto si acabas de subir justo al máximo nivel con uno de tus personajes o necesitas blasones del alba de héroe para mejorar tu equipo, los Lugares del Ritual se han convertido en una actividad muy interesante." },
            { type = "heading", text = "Preparando el método de farmeo" },
            { type = "paragraph", text = "Esta noticia es contenido mock para validar la interfaz del addon. En la siguiente fase será generada automáticamente desde el RSS de AlterTime." },
            { type = "bullet", text = "Zarcillos: muévete cuando aparezcan debajo del personaje." },
            { type = "bullet", text = "Manifestaciones: pueden ser interrumpidas o aturdidas." },
            { type = "bullet", text = "Patrullas: visibles en el mapa y evitables." },
        },
    },
    {
        id = "mock-002",
        slug = "spelloverlay-enhanced",
        title = "Personaliza las alertas de hechizo de tu personaje gracias al addon SpellOverlay Enhanced",
        excerpt = "¡No te lo pierdas!",
        author = "Pixpo",
        publishedAt = 1759990000,
        categories = { "Retail", "Ayuda y Addons", "Addons" },
        url = "https://altertime.es/",
        cover = nil,
        body = {
            { type = "paragraph", text = "Ejemplo de noticia de addons para probar el layout, los metadatos, las categorías y el marcado de noticias vistas." },
            { type = "heading", text = "Vista de artículo" },
            { type = "paragraph", text = "La versión 0.2.0-alpha soporta filtros, búsqueda, fecha, contador de resultados y enlace original copiable." },
        },
    },
}
