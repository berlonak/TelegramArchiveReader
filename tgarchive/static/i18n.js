// copyright by berlonak
// telegram: @Kilax123
'use strict';
// UI translations. Russian is the original language and the fallback for missing keys.
const I18N = {
  ru: {
    'lang.switch': '⇄ English', 'lang.short': 'English',
    'title': 'Архив переписок',
    'login.title': 'Архив переписок', 'login.subtitle': 'Доступ по паролю.', 'login.label': 'Пароль архива',
    'login.placeholder': 'Введите пароль', 'login.show': 'Показать пароль', 'login.submit': 'Войти',
    'login.footer': 'Только чтение', 'loading': 'Загружаем архив…',
    'brand.subtitle': 'История сообщений', 'sidebar.hide': 'Скрыть панель', 'menu': 'Меню',
    'menu.theme': '☼ Переключить тему', 'menu.logout': '↪ Выйти из архива',
    'nav.home': 'Обзор', 'nav.search': 'Поиск по архиву', 'nav.contacts': 'Контакты',
    'nav.gallery': 'Медиатека', 'nav.bookmarks': 'Закладки',
    'sidebar.section': 'СООБЩЕНИЯ', 'sidebar.filter': 'Найти чат или канал…', 'sidebar.filterLabel': 'Поиск чата',
    'cat.all': 'Все', 'cat.personal': 'Личные', 'cat.groups': 'Группы', 'cat.channels': 'Каналы',
    'cat.saved': 'Избранное', 'cat.left': 'Покинутые',
    'sidebar.status': 'Архив · Только чтение', 'logout': 'Выход', 'sidebar.open': 'Открыть список чатов',
    'home.badge': 'АРХИВ TELEGRAM', 'home.title': 'Архив сообщений',
    'home.description': 'Чаты, группы, каналы и файлы из экспорта Telegram.',
    'home.search': '⌕  Искать по всему архиву', 'home.media': '▧  Открыть медиатеку',
    'chat.search': 'Поиск в чате', 'chat.media': 'Медиа чата', 'chat.dates': 'Даты сообщений', 'chat.latest': 'Последние сообщения',
    'calendar.title': 'Перейти к дате', 'calendar.date': 'Дата', 'calendar.go': 'Найти сообщения',
    'readonly': '🔒  Архивная копия · Отправка сообщений отключена', 'latest': '↓ К последним',
    'search.overline': 'ПОИСК', 'search.title': 'Поиск сообщений',
    'search.description': 'Ищите по всем перепискам сразу — включая группы, каналы и имена файлов.',
    'search.placeholder': 'Сообщение, фраза или название файла…', 'search.submit': 'Искать →',
    'search.chat': 'Чат', 'search.allChats': 'Все чаты', 'search.sender': 'Отправитель', 'search.senderPlaceholder': 'Имя',
    'search.after': 'С даты', 'search.before': 'По дату', 'search.has': 'Содержит',
    'has.any': 'Всё', 'has.photo': 'Фото', 'has.video': 'Видео', 'has.voice': 'Голосовые', 'has.audio': 'Аудио',
    'has.file': 'Файл', 'has.link': 'Ссылку',
    'search.enter': 'Введите запрос', 'search.more': 'Загрузить ещё ↓', 'search.searching': 'Ищем…',
    'search.error': 'Ошибка поиска', 'search.results': 'Результаты: {n}', 'search.none': 'Совпадений не найдено',
    'search.hint': 'Нажмите на результат, чтобы открыть исходное сообщение',
    'search.tryOther': 'Попробуйте другое слово или измените фильтры.', 'search.attachment': '📎 Вложение',
    'contacts.title': 'Контакты из экспорта',
    'contacts.description': 'Список контактов на дату экспорта. Для переписок с людьми, которых больше нет в списке, откройте «Личные» и ищите по названию чата. Удалённую до экспорта историю восстановить нельзя.',
    'contacts.personal': 'Показать все личные чаты', 'contacts.placeholder': 'Имя или номер телефона',
    'contacts.label': 'Поиск контакта', 'contacts.more': 'Ещё контакты ↓', 'contacts.noName': 'Без имени',
    'contacts.find': 'Найти переписку', 'contacts.shown': 'Показано: {n}',
    'contacts.none': 'Контактов нет. Проверьте, выполнено ли обновление индекса контактов.',
    'gallery.overline': 'ФАЙЛЫ', 'gallery.title': 'Медиатека',
    'gallery.description': 'Фото, видео, аудио и документы из всех чатов.', 'gallery.chatDescription': 'Медиа выбранного чата',
    'gallery.all': 'Всё', 'gallery.photo': 'Фото', 'gallery.video': 'Видео', 'gallery.voice': 'Голосовые',
    'gallery.audio': 'Аудио', 'gallery.file': 'Файлы', 'gallery.sticker': 'Стикеры', 'gallery.more': 'Показать ещё ↓',
    'gallery.empty': 'В этой категории ничего нет',
    'bookmarks.overline': 'СОХРАНЁННОЕ', 'bookmarks.title': 'Закладки',
    'bookmarks.description': 'Здесь сохраняются отмеченные сообщения со ссылкой на исходный чат.',
    'bookmarks.empty': 'Пока пусто. Откройте сообщение и нажмите ☆, чтобы сохранить.',
    'bookmarks.added': 'Сообщение добавлено в закладки', 'bookmarks.removed': 'Закладка удалена',
    'bookmarks.add': 'В закладки', 'bookmarks.remove': 'Удалить закладку',
    'viewer.download': '↓ Скачать', 'viewer.close': 'Закрыть', 'viewer.message': 'К сообщению ↗', 'viewer.media': 'Медиа',
    'viewer.downloadFile': '↓ Скачать файл: {name}', 'viewer.raw': 'Исходные данные Telegram JSON',
    'error.request': 'Не удалось выполнить запрос', 'error.session': 'Сессия завершена. Войдите снова.',
    'error.http': 'Ошибка HTTP {status}',
    'chats.none': 'Чаты не найдены', 'chat.untitled': 'Переписка',
    'kind.channels': 'Канал', 'kind.groups': 'Группа', 'kind.saved': 'Избранное', 'kind.personal': 'Личный чат', 'kind.other': 'Чат',
    'chat.left': ' · Покинутый',
    'chat.messages': {one: '{n} сообщение', few: '{n} сообщения', many: '{n} сообщений', other: '{n} сообщения'},
    'chat.loading': 'Загружаем историю…', 'chat.empty': 'В этом чате пока нет сообщений',
    'chat.older': '↑ Загрузить старые сообщения', 'chat.newer': '↓ Загрузить следующие сообщения', 'chat.loadingMore': 'Загружаем…',
    'stats.updated': 'Обновлено: {date}', 'stats.empty': 'Архив пока пуст', 'stats.chats': 'Чатов, групп и каналов',
    'stats.messages': 'Сообщений', 'stats.photos': 'Фотографий', 'stats.videos': 'Видео',
    'message.spoiler': 'Нажмите, чтобы раскрыть', 'message.forwarded': '↪ Переслано от {name}',
    'message.replyTo': 'Ответ на сообщение', 'message.number': 'Сообщение {id}', 'message.goTo': 'Перейти к сообщению',
    'message.fallback': 'Сообщение', 'message.edited': ' · ред.', 'message.raw': 'Посмотреть исходный JSON',
    'media.photo': 'Фото', 'media.downloadVideo': '↓ Скачать видео', 'media.downloadAudio': '↓ Скачать аудио', 'media.file': 'Файл',
    'calendar.searching': 'Ищем дату…', 'calendar.noneThatDay': 'В этот день сообщений нет.',
    'calendar.days': 'Дней с сообщениями: {n}', 'calendar.noMessages': 'Нет сообщений',
  },
  en: {
    'lang.switch': '⇄ Русский', 'lang.short': 'Русский',
    'title': 'Message Archive',
    'login.title': 'Message Archive', 'login.subtitle': 'Password-protected access.', 'login.label': 'Archive password',
    'login.placeholder': 'Enter password', 'login.show': 'Show password', 'login.submit': 'Sign in',
    'login.footer': 'Read-only', 'loading': 'Loading archive…',
    'brand.subtitle': 'Message history', 'sidebar.hide': 'Hide panel', 'menu': 'Menu',
    'menu.theme': '☼ Toggle theme', 'menu.logout': '↪ Sign out',
    'nav.home': 'Overview', 'nav.search': 'Search archive', 'nav.contacts': 'Contacts',
    'nav.gallery': 'Media library', 'nav.bookmarks': 'Bookmarks',
    'sidebar.section': 'CHATS', 'sidebar.filter': 'Find a chat or channel…', 'sidebar.filterLabel': 'Search chats',
    'cat.all': 'All', 'cat.personal': 'Personal', 'cat.groups': 'Groups', 'cat.channels': 'Channels',
    'cat.saved': 'Saved', 'cat.left': 'Left',
    'sidebar.status': 'Archive · Read-only', 'logout': 'Sign out', 'sidebar.open': 'Open chat list',
    'home.badge': 'TELEGRAM ARCHIVE', 'home.title': 'Message archive',
    'home.description': 'Chats, groups, channels and files from your Telegram export.',
    'home.search': '⌕  Search the whole archive', 'home.media': '▧  Open media library',
    'chat.search': 'Search in chat', 'chat.media': 'Chat media', 'chat.dates': 'Message dates', 'chat.latest': 'Latest messages',
    'calendar.title': 'Jump to date', 'calendar.date': 'Date', 'calendar.go': 'Find messages',
    'readonly': '🔒  Archived copy · Sending messages is disabled', 'latest': '↓ Latest',
    'search.overline': 'SEARCH', 'search.title': 'Message search',
    'search.description': 'Search all conversations at once, including groups, channels and file names.',
    'search.placeholder': 'Message, phrase or file name…', 'search.submit': 'Search →',
    'search.chat': 'Chat', 'search.allChats': 'All chats', 'search.sender': 'Sender', 'search.senderPlaceholder': 'Name',
    'search.after': 'From', 'search.before': 'To', 'search.has': 'Contains',
    'has.any': 'Anything', 'has.photo': 'Photo', 'has.video': 'Video', 'has.voice': 'Voice message', 'has.audio': 'Audio',
    'has.file': 'File', 'has.link': 'Link',
    'search.enter': 'Enter a query', 'search.more': 'Load more ↓', 'search.searching': 'Searching…',
    'search.error': 'Search failed', 'search.results': 'Results: {n}', 'search.none': 'No matches found',
    'search.hint': 'Click a result to open the message in its chat',
    'search.tryOther': 'Try another word or change the filters.', 'search.attachment': '📎 Attachment',
    'contacts.title': 'Contacts from the export',
    'contacts.description': 'Your contact list as of the export date. For people who are no longer in the list, open “Personal” and search by chat name. History deleted before the export cannot be recovered.',
    'contacts.personal': 'Show all personal chats', 'contacts.placeholder': 'Name or phone number',
    'contacts.label': 'Search contacts', 'contacts.more': 'More contacts ↓', 'contacts.noName': 'No name',
    'contacts.find': 'Find conversation', 'contacts.shown': 'Shown: {n}',
    'contacts.none': 'No contacts. Check that the contacts index has been built.',
    'gallery.overline': 'FILES', 'gallery.title': 'Media library',
    'gallery.description': 'Photos, videos, audio and documents from all chats.', 'gallery.chatDescription': 'Media from the selected chat',
    'gallery.all': 'All', 'gallery.photo': 'Photos', 'gallery.video': 'Videos', 'gallery.voice': 'Voice',
    'gallery.audio': 'Audio', 'gallery.file': 'Files', 'gallery.sticker': 'Stickers', 'gallery.more': 'Show more ↓',
    'gallery.empty': 'Nothing in this category',
    'bookmarks.overline': 'SAVED', 'bookmarks.title': 'Bookmarks',
    'bookmarks.description': 'Messages you bookmark are kept here with a link to their chat.',
    'bookmarks.empty': 'Nothing here yet. Open a message and press ☆ to save it.',
    'bookmarks.added': 'Message bookmarked', 'bookmarks.removed': 'Bookmark removed',
    'bookmarks.add': 'Bookmark', 'bookmarks.remove': 'Remove bookmark',
    'viewer.download': '↓ Download', 'viewer.close': 'Close', 'viewer.message': 'Go to message ↗', 'viewer.media': 'Media',
    'viewer.downloadFile': '↓ Download file: {name}', 'viewer.raw': 'Raw Telegram JSON',
    'error.request': 'Request failed', 'error.session': 'Session ended. Please sign in again.',
    'error.http': 'HTTP error {status}',
    'chats.none': 'No chats found', 'chat.untitled': 'Conversation',
    'kind.channels': 'Channel', 'kind.groups': 'Group', 'kind.saved': 'Saved Messages', 'kind.personal': 'Personal chat', 'kind.other': 'Chat',
    'chat.left': ' · Left',
    'chat.messages': {one: '{n} message', other: '{n} messages'},
    'chat.loading': 'Loading history…', 'chat.empty': 'This chat has no messages yet',
    'chat.older': '↑ Load older messages', 'chat.newer': '↓ Load newer messages', 'chat.loadingMore': 'Loading…',
    'stats.updated': 'Updated: {date}', 'stats.empty': 'The archive is empty', 'stats.chats': 'Chats, groups and channels',
    'stats.messages': 'Messages', 'stats.photos': 'Photos', 'stats.videos': 'Videos',
    'message.spoiler': 'Click to reveal', 'message.forwarded': '↪ Forwarded from {name}',
    'message.replyTo': 'Reply to a message', 'message.number': 'Message {id}', 'message.goTo': 'Go to message',
    'message.fallback': 'Message', 'message.edited': ' · edited', 'message.raw': 'View raw JSON',
    'media.photo': 'Photo', 'media.downloadVideo': '↓ Download video', 'media.downloadAudio': '↓ Download audio', 'media.file': 'File',
    'calendar.searching': 'Looking for the date…', 'calendar.noneThatDay': 'No messages on this day.',
    'calendar.days': 'Days with messages: {n}', 'calendar.noMessages': 'No messages',
  },
};
// Server error details are Russian (a few are English); translate the known ones for display.
const SERVER_TEXT = {
  'Требуется вход': 'Sign-in required',
  'Сессия истекла': 'Session expired',
  'Слишком много попыток. Попробуйте через 15 минут.': 'Too many attempts. Try again in 15 minutes.',
  'Архив не настроен: запустите tgarchive init': 'The archive is not set up: run tgarchive init',
  'Неверный пароль': 'Wrong password',
  'Чат не найден': 'Chat not found',
  'Сообщение не найдено': 'Message not found',
  'Нужно указать время и ID сообщения': 'Both the timestamp and the message ID are required',
  'Нельзя одновременно загружать старые и новые сообщения': 'Cannot load older and newer messages at the same time',
  'Дата должна быть YYYY-MM-DD': 'The date must be YYYY-MM-DD',
  'Неизвестный тип медиа': 'Unknown media type',
  'Файл не найден': 'File not found',
  'Не указан TGARCHIVE_BUNDLE_ROOT': 'TGARCHIVE_BUNDLE_ROOT is not set',
  'Недопустимый путь к экспорту': 'Invalid export path',
  'Путь вне архива': 'Path is outside the archive',
  'Неверный путь': 'Invalid path',
  'Исходный файл недоступен. Проверьте путь к экспорту.': 'The source file is unavailable. Check the export path.',
  'Нет аватара': 'No avatar',
  'Неподдерживаемый аватар': 'Unsupported avatar',
  'Сообщение отсутствует в экспорте': 'This message is not in the export',
};
const SERVER_TEXT_RU = {
  'Cross-origin request forbidden': 'Запрос с другого сайта запрещён',
  'Origin mismatch': 'Источник запроса не совпадает с адресом сайта',
  'HTTPS required': 'Требуется HTTPS',
  'application/json required': 'Требуется application/json',
};
const LANGS = ['ru', 'en'];
let LANG = (() => {
  try { const saved = localStorage.getItem('tgarchive-lang'); if (LANGS.includes(saved)) return saved; } catch {}
  const preferred = (navigator.languages && navigator.languages[0]) || navigator.language || '';
  return /^(ru|uk|be|kk)\b/i.test(preferred) ? 'ru' : 'en';
})();
const locale = () => (LANG === 'ru' ? 'ru-RU' : 'en-US');
function t(key, vars = {}) {
  const value = I18N[LANG][key] ?? I18N.ru[key] ?? key;
  return String(value).replace(/\{(\w+)\}/g, (match, name) => (name in vars ? String(vars[name]) : match));
}
function tn(key, count, formatted = String(count)) {
  const forms = I18N[LANG][key] ?? I18N.ru[key];
  const rule = new Intl.PluralRules(locale()).select(Number(count) || 0);
  return (forms[rule] ?? forms.other).replace('{n}', formatted);
}
function serverText(detail) {
  if (LANG === 'en') return SERVER_TEXT[detail] ?? detail;
  return SERVER_TEXT_RU[detail] ?? detail;
}
// data-i18n replaces an element's text. If the element also holds icons (child elements),
// only its first non-empty text node is replaced, so icon markup and styles stay intact.
function translateElement(element, text) {
  if (!element.children.length) { element.textContent = text; return; }
  for (const node of element.childNodes) {
    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
      const lead = /^\s/.test(node.textContent) ? ' ' : '';
      const trail = /\s$/.test(node.textContent) ? ' ' : '';
      node.textContent = lead + text + trail;
      return;
    }
  }
  element.prepend(document.createTextNode(text + ' '));
}
function applyI18n(root = document) {
  document.documentElement.lang = LANG;
  document.title = t('title');
  for (const el of root.querySelectorAll('[data-i18n]')) translateElement(el, t(el.dataset.i18n));
  for (const el of root.querySelectorAll('[data-i18n-placeholder]')) el.placeholder = t(el.dataset.i18nPlaceholder);
  for (const el of root.querySelectorAll('[data-i18n-title]')) el.title = t(el.dataset.i18nTitle);
  for (const el of root.querySelectorAll('[data-i18n-aria]')) el.setAttribute('aria-label', t(el.dataset.i18nAria));
}
function setLanguage(lang) {
  if (!LANGS.includes(lang) || lang === LANG) return;
  LANG = lang;
  try { localStorage.setItem('tgarchive-lang', lang); } catch {}
  applyI18n();
  document.dispatchEvent(new CustomEvent('tgarchive:language'));
}
function toggleLanguage() { setLanguage(LANG === 'ru' ? 'en' : 'ru'); }
