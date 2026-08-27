export const MESSAGE_PREFERENCES_STORAGE_KEY = "atanes-messages-preferences:v1";

export const DEFAULT_PANEL_SIZE = { width: 360, height: 570 } as const;

export const MESSAGE_BACKGROUND_OPTIONS = [
  { value: "#FFFFFF", label: "Blanco" },
  { value: "#F7F7F5", label: "Gris muy claro" },
  { value: "#F1F6F2", label: "Verde Atanes suave" },
  { value: "#E6F8B2", label: "Lima Atanes suave" },
  { value: "#EEF5D8", label: "Acento Atanes suave" },
] as const;

export const MESSAGE_FONT_OPTIONS = [
  { value: "default", label: "Predeterminada de Atanes", family: "Arial, Helvetica, sans-serif" },
  { value: "arial", label: "Arial", family: "Arial, sans-serif" },
  { value: "georgia", label: "Georgia", family: "Georgia, serif" },
  { value: "verdana", label: "Verdana", family: "Verdana, sans-serif" },
  { value: "trebuchet", label: "Trebuchet MS", family: "'Trebuchet MS', sans-serif" },
  { value: "courier", label: "Courier New", family: "'Courier New', monospace" },
] as const;

export type MessageFontId = (typeof MESSAGE_FONT_OPTIONS)[number]["value"];

export type MessagePreferences = {
  panelWidth: number;
  panelHeight: number;
  backgroundColor: string;
  font: MessageFontId;
};

export const DEFAULT_MESSAGE_PREFERENCES: MessagePreferences = {
  panelWidth: DEFAULT_PANEL_SIZE.width,
  panelHeight: DEFAULT_PANEL_SIZE.height,
  backgroundColor: MESSAGE_BACKGROUND_OPTIONS[0].value,
  font: MESSAGE_FONT_OPTIONS[0].value,
};

export function parseMessagePreferences(value: string | null): MessagePreferences {
  if (!value) return DEFAULT_MESSAGE_PREFERENCES;

  try {
    const stored = JSON.parse(value) as Partial<MessagePreferences>;
    const backgroundColor = MESSAGE_BACKGROUND_OPTIONS.some((option) => option.value === stored.backgroundColor)
      ? stored.backgroundColor!
      : DEFAULT_MESSAGE_PREFERENCES.backgroundColor;
    const font = MESSAGE_FONT_OPTIONS.some((option) => option.value === stored.font)
      ? stored.font!
      : DEFAULT_MESSAGE_PREFERENCES.font;

    return {
      panelWidth: typeof stored.panelWidth === "number" && Number.isFinite(stored.panelWidth)
        ? stored.panelWidth
        : DEFAULT_MESSAGE_PREFERENCES.panelWidth,
      panelHeight: typeof stored.panelHeight === "number" && Number.isFinite(stored.panelHeight)
        ? stored.panelHeight
        : DEFAULT_MESSAGE_PREFERENCES.panelHeight,
      backgroundColor,
      font,
    };
  } catch {
    return DEFAULT_MESSAGE_PREFERENCES;
  }
}

export function messageFontFamily(font: MessageFontId) {
  return MESSAGE_FONT_OPTIONS.find((option) => option.value === font)?.family ?? MESSAGE_FONT_OPTIONS[0].family;
}

const IMAGE_DATABASE = "atanes-message-preferences";
const IMAGE_STORE = "backgrounds";
const IMAGE_KEY = "chat-background-v1";

function openImageDatabase() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(IMAGE_DATABASE, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(IMAGE_STORE)) {
        request.result.createObjectStore(IMAGE_STORE);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("No se pudo abrir el almacenamiento local."));
  });
}

function imageTransaction(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest) {
  return openImageDatabase().then((database) => new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(IMAGE_STORE, mode);
    action(transaction.objectStore(IMAGE_STORE));
    transaction.oncomplete = () => {
      database.close();
      resolve();
    };
    transaction.onerror = () => {
      database.close();
      reject(transaction.error ?? new Error("No se pudo guardar la preferencia local."));
    };
    transaction.onabort = transaction.onerror;
  }));
}

export async function loadMessageBackgroundImage() {
  const database = await openImageDatabase();
  return new Promise<Blob | null>((resolve, reject) => {
    const transaction = database.transaction(IMAGE_STORE, "readonly");
    const request = transaction.objectStore(IMAGE_STORE).get(IMAGE_KEY);
    request.onsuccess = () => resolve(request.result instanceof Blob ? request.result : null);
    request.onerror = () => reject(request.error ?? new Error("No se pudo recuperar la imagen de fondo."));
    transaction.oncomplete = () => database.close();
    transaction.onerror = () => database.close();
  });
}

export function saveMessageBackgroundImage(image: Blob) {
  return imageTransaction("readwrite", (store) => store.put(image, IMAGE_KEY));
}

export function deleteMessageBackgroundImage() {
  return imageTransaction("readwrite", (store) => store.delete(IMAGE_KEY));
}
