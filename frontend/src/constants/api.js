/* Endpoints del backend centralizados */
export const API_AUTH_LOGIN = '/api/auth/login'
export const API_CONTACTS = '/api/contacts'
export const API_CONTACTS_SEARCH_AI = '/api/contacts/search-ai'
export const API_CONTACTS_SAVE = '/api/contacts/save-selection'
export const API_CONTACTS_MANUAL = '/api/contacts/manual'
export const API_CONTACT_DELETE = (id) => `/api/contacts/${id}`
export const API_CONTACT_ENRICH = (id) => `/api/contacts/${id}/enrich`
export const API_COMPOSE_GENERATE = '/api/compose/generate'
export const API_COMPOSE_FROM_CONTACTS = '/api/compose/generate-from-contacts'
export const API_COMPOSE_TEMPLATES = '/api/compose/templates'
export const API_COMPOSE_FORMAT_MANUAL = '/api/compose/format-manual'
export const API_SEND_CAMPAIGN = '/api/send/campaign'
export const API_SEND_CAMPAIGNS = '/api/send/campaigns'
export const API_SEND_STATS = '/api/send/stats'
export const API_SEND_DASHBOARD = '/api/send/dashboard'
export const API_SEND_CAMPAIGN_STATS = (id) => `/api/send/campaigns/${id}/stats`
export const API_REPLIES = '/api/replies'
export const API_REPLIES_SYNC = (id) => `/api/replies/${id}/sync`
export const API_REPLIES_RESPOND = (id) => `/api/replies/${id}/respond`
export const API_REPLIES_READ = (id) => `/api/replies/${id}/read`
export const API_BLOQUES = '/api/bloques'
export const API_BLOQUE_CONTACTOS = (id) => `/api/bloques/${id}/contactos`
export const API_BLOQUE_DELETE = (id) => `/api/bloques/${id}`
export const API_BLOQUE_REMOVE_CONTACT = (bid, cid) => `/api/bloques/${bid}/contactos/${cid}`
export const API_APOLLO_STATUS = '/api/apollo/status'
export const API_APOLLO_CONFIG = '/api/apollo/config'
export const API_APOLLO_SEARCH = '/api/apollo/search'
export const API_PERPLEXITY_STATUS = '/api/perplexity/status'
export const API_PERPLEXITY_CONFIG = '/api/perplexity/config'
export const API_PERPLEXITY_SEARCH = '/api/perplexity/search'
export const API_APIFY_STATUS = '/api/apify/status'
export const API_APIFY_CONFIG = '/api/apify/config'
export const API_APIFY_SEARCH = '/api/apify/buscar'
export const API_APIFY_ENRICH = '/api/apify/enriquecer-contacto'
export const API_ADMIN_USUARIOS = '/api/admin/usuarios'
export const API_ADMIN_USUARIO = (id) => `/api/admin/usuarios/${id}`
export const API_CAMPANAS_PROGRAMADAS = '/api/campanas-programadas'
export const API_CAMPANA_PROGRAMADA_CANCEL = (id) => `/api/campanas-programadas/${id}`
