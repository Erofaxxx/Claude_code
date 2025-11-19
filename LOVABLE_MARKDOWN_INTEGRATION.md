# Интеграция AI CSV Agent с Lovable (Markdown подход)

## Обзор изменений

AI агент теперь возвращает результаты в **Markdown формате** для максимальной гибкости и красивого отображения.

### Формат API ответа

```json
{
  "success": true,
  "query": "проанализируй продажи",
  "result_data": "## Анализ продаж\n\nПроанализировал 1000 записей...\n\n| Страна | Выручка |\n|--------|----------|\n| Cuba | $27.5M |",
  "text_output": "Начинаю анализ... Данные успешно загружены...",
  "plots": ["data:image/png;base64,..."],
  "final_code": "# сгенерированный Python код",
  "timestamp": "2025-11-18T23:00:00"
}
```

**Ключевые поля:**
- `result_data` - **Markdown строка** с результатами анализа (таблицы, списки, текст)
- `text_output` - текстовые логи выполнения (из print())
- `plots` - массив графиков в base64
- `final_code` - сгенерированный Python код

## Установка зависимостей

```bash
npm install react-markdown remark-gfm rehype-sanitize
```

**Библиотеки:**
- `react-markdown` - рендеринг Markdown в React
- `remark-gfm` - поддержка GitHub Flavored Markdown (таблицы, strikethrough и т.д.)
- `rehype-sanitize` - безопасность (санитизация HTML)

## Код интеграции

### 1. Импорты

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
```

### 2. Компонент для отображения результата

```tsx
const AnalysisResult = ({ message }: { message: AnalysisMessage }) => {
  return (
    <div className="space-y-4">
      {/* Текстовый вывод (логи) */}
      {message.text_output && (
        <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 font-mono whitespace-pre-wrap border border-gray-200">
          {message.text_output}
        </div>
      )}

      {/* Основной результат в Markdown */}
      {message.result_data && typeof message.result_data === 'string' && (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
            components={{
              // Кастомизация таблиц
              table: ({ node, ...props }) => (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full divide-y divide-gray-200 border border-gray-300" {...props} />
                </div>
              ),
              thead: ({ node, ...props }) => (
                <thead className="bg-gray-50" {...props} />
              ),
              th: ({ node, ...props }) => (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border-b border-gray-300" {...props} />
              ),
              td: ({ node, ...props }) => (
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 border-b border-gray-200" {...props} />
              ),
              // Кастомизация заголовков
              h2: ({ node, ...props }) => (
                <h2 className="text-2xl font-bold text-gray-900 mt-6 mb-4" {...props} />
              ),
              h3: ({ node, ...props }) => (
                <h3 className="text-xl font-semibold text-gray-800 mt-4 mb-3" {...props} />
              ),
              // Кастомизация списков
              ul: ({ node, ...props }) => (
                <ul className="list-disc list-inside space-y-1 my-3" {...props} />
              ),
              ol: ({ node, ...props }) => (
                <ol className="list-decimal list-inside space-y-1 my-3" {...props} />
              ),
              li: ({ node, ...props }) => (
                <li className="text-gray-800" {...props} />
              ),
              // Кастомизация выделения
              strong: ({ node, ...props }) => (
                <strong className="font-bold text-gray-900" {...props} />
              ),
              em: ({ node, ...props }) => (
                <em className="italic text-gray-700" {...props} />
              ),
              // Разделительная линия
              hr: ({ node, ...props }) => (
                <hr className="my-6 border-gray-300" {...props} />
              ),
              // Параграфы
              p: ({ node, ...props }) => (
                <p className="text-gray-800 my-2 leading-relaxed" {...props} />
              ),
            }}
          >
            {message.result_data}
          </ReactMarkdown>
        </div>
      )}

      {/* Графики */}
      {message.plots && message.plots.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-800">📊 Визуализации</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {message.plots.map((plot: string, idx: number) => (
              <div key={idx} className="rounded-lg overflow-hidden border border-gray-200 shadow-sm">
                <img
                  src={plot}
                  alt={`График ${idx + 1}`}
                  className="w-full h-auto"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Код (опционально, collapsible) */}
      {message.final_code && (
        <details className="group">
          <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900 flex items-center gap-2">
            <span className="group-open:rotate-90 transition-transform">▶</span>
            Показать сгенерированный код
          </summary>
          <pre className="mt-2 p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-sm">
            <code>{message.final_code}</code>
          </pre>
        </details>
      )}
    </div>
  );
};
```

### 3. Стили Tailwind (добавить в tailwind.config.js)

```js
module.exports = {
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
```

Установи плагин:
```bash
npm install @tailwindcss/typography
```

## Пример использования в чате

```tsx
const ChatMessage = ({ message }: { message: Message }) => {
  if (message.role === 'user') {
    return <div className="text-right">{message.content}</div>;
  }

  if (message.role === 'assistant' && message.analysisResult) {
    return <AnalysisResult message={message.analysisResult} />;
  }

  return <div>{message.content}</div>;
};
```

## Отправка запроса к API

```tsx
const analyzeCSV = async (file: File, query: string, chatHistory: any[]) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('query', query);
  formData.append('chat_history', JSON.stringify(chatHistory));

  const response = await fetch('https://julius.sopods.store/api/analyze', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();

  if (!data.success) {
    throw new Error(data.error || 'Analysis failed');
  }

  return data;
};
```

## Множественные файлы

Для анализа нескольких CSV файлов используй endpoint `/api/analyze-multi`:

```tsx
const analyzeMultipleCSV = async (files: File[], query: string) => {
  const formData = new FormData();

  files.forEach(file => {
    formData.append('files', file);
  });

  formData.append('query', query);

  const response = await fetch('https://julius.sopods.store/api/analyze-multi', {
    method: 'POST',
    body: formData,
  });

  return await response.json();
};
```

## Примеры Markdown результатов

### Пример 1: Простой анализ

**Запрос:** "какая средняя зарплата?"

**result_data:**
```markdown
## Анализ зарплат

Проанализировал данные по 51 штату.

**Средняя зарплата:** $51,667

Данные показывают стабильную динамику роста.
```

### Пример 2: Таблица

**Запрос:** "топ-5 стран по выручке"

**result_data:**
```markdown
## Топ-5 стран по выручке

| Страна | Выручка | Доля рынка |
|--------|---------|------------|
| Cuba | $27,522,085 | 12.5% |
| Ghana | $21,267,908 | 9.8% |
| Costa Rica | $19,628,279 | 9.1% |
| Iran | $18,719,532 | 8.7% |
| Panama | $16,453,921 | 7.6% |

---

**Вывод:** Cuba доминирует с 12.5% общей выручки
```

### Пример 3: Комплексный анализ

**Запрос:** "проанализируй продажи"

**result_data:**
```markdown
## Анализ продаж

Проанализировал 1000 записей продаж за последний год.

### Общая статистика

| Метрика | Значение |
|---------|----------|
| Общая выручка | $1,327,321,840 |
| Общая прибыль | $391,202,611 |
| Рентабельность | 29.5% |

### Топ категории

1. **Cosmetics** - $74M прибыли
2. **Household** - $61M прибыли
3. **Office Supplies** - $56M прибыли

### Каналы продаж

- **Offline:** 52.7% выручки
- **Online:** 47.3% выручки

---

**Выводы:**
- Бизнес показывает здоровый рост
- Offline каналы все еще лидируют, но online быстро растет
- Категория Cosmetics - наш основной драйвер прибыли
```

## Преимущества Markdown подхода

✅ **Гибкость** - AI может форматировать как угодно (таблицы, списки, заголовки)
✅ **Простота** - AI отлично знает Markdown
✅ **Безопасность** - rehype-sanitize защищает от XSS
✅ **Красота** - готовые стили через @tailwindcss/typography
✅ **Читаемость** - даже сырой Markdown читается хорошо
✅ **Расширяемость** - легко добавлять кастомные компоненты

## Обработка ошибок

```tsx
const AnalysisResult = ({ message }: { message: AnalysisMessage }) => {
  // Если API вернул ошибку
  if (!message.success) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold mb-2">❌ Ошибка анализа</h3>
        <p className="text-red-700 text-sm">{message.error}</p>
        {message.error_details && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-red-600">Детали</summary>
            <pre className="mt-2 text-xs overflow-x-auto">{message.error_details}</pre>
          </details>
        )}
      </div>
    );
  }

  // Если нет результата
  if (!message.result_data && !message.plots) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">⚠️ Анализ завершен, но результатов нет</p>
      </div>
    );
  }

  // Нормальный рендеринг...
  return (
    // ... код из примера выше
  );
};
```

## TypeScript типы

```typescript
interface AnalysisMessage {
  success: boolean;
  query: string;
  result_data?: string;  // Markdown строка
  text_output?: string;  // Логи
  plots?: string[];      // Base64 images
  final_code?: string;   // Python код
  error?: string;
  error_details?: string;
  timestamp: string;
  attempts_count?: number;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content?: string;
  analysisResult?: AnalysisMessage;
  timestamp: Date;
}
```

## Полный пример компонента чата

```tsx
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

export const CSVAnalysisChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !query) return;

    // Добавляем сообщение пользователя
    const userMessage: ChatMessage = {
      role: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    setLoading(true);
    try {
      const result = await analyzeCSV(file, query, messages);

      // Добавляем ответ агента
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        analysisResult: result,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);

      setQuery('');
    } catch (error) {
      console.error('Analysis failed:', error);
      // Показать ошибку пользователю
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Загрузка файла */}
      <div className="p-4 border-b">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-sm"
        />
      </div>

      {/* Сообщения */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}
        {loading && <div>Анализирую...</div>}
      </div>

      {/* Ввод запроса */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Задайте вопрос о данных..."
            className="flex-1 px-4 py-2 border rounded-lg"
            disabled={!file || loading}
          />
          <button
            type="submit"
            disabled={!file || !query || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50"
          >
            Отправить
          </button>
        </div>
      </form>
    </div>
  );
};
```

## Готово! 🎉

Теперь твой AI агент будет выводить красиво отформатированные результаты в Markdown, а Lovable будет рендерить их с полной поддержкой таблиц, списков, заголовков и стилей!
