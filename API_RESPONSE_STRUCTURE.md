# API Response Structure - Структура ответа API

## Формат ответа `/api/analyze`

```json
{
  "success": true,
  "query": "Построй график по годам",
  "result_data": "## 📊 Результаты анализа\n\n| Год | Сумма |\n...",
  "text_output": "🔍 ШАГ 1: Изучаю структуру данных...\n🧹 ШАГ 2...",
  "plots": ["data:image/png;base64,..."],
  "code_attempts": [...],
  "final_code": "print('...')\n...",
  "timestamp": "2025-11-23T...",
  "model_info": {
    "model_key": "claude-sonnet-4.5",
    "model_name": "Claude Sonnet 4.5",
    "provider": "Anthropic"
  }
}
```

## Поля ответа

### `result_data` - Основной результат
**ЧТО**: Финальный отчет в формате Markdown
**КАК ПОКАЗЫВАТЬ**: Рендерить как Markdown с поддержкой таблиц, заголовков, эмодзи

```markdown
## 📊 Результаты анализа

| Год | Сумма |
|-----|-------|
| 2019 | 1,234,567 |
| 2020 | 2,345,678 |

✅ Анализ выполнен
```

### `text_output` - Логи выполнения (Julius.ai style)
**ЧТО**: Пошаговые логи работы AI (print() из Python кода)
**КАК ПОКАЗЫВАТЬ**: В collapsible/expandable секции "Логи выполнения" или "Детали"

```
🔍 ШАГ 1: Изучаю структуру данных...
Размер данных: 1052 строк, 31 колонок
Колонки: ['Year', 'State', 'Totals.Capital outlay', ...]

🧹 ШАГ 2: Проверяю качество данных...
✅ Найдены колонки:
   - Год: 'Year'
   - Капитальные расходы: 'Totals.Capital outlay'

🔄 Преобразую типы данных...
   - Year: int64
   - Totals.Capital outlay: float64

✅ Данные очищены: 1045 валидных строк из 1052

📊 ШАГ 3: Выполняю анализ...
✅ Агрегировано данных по годам: 21 периодов
   - Период: 1992 - 2019

📈 ШАГ 4: Создаю визуализацию...
✅ График создан успешно

✅ ШАГ 5: Формирую финальный отчет...
✅ Анализ завершен успешно!
```

### `plots` - Графики
**ЧТО**: Массив Base64 изображений
**КАК ПОКАЗЫВАТЬ**: `<img src="data:image/png;base64,..." />`

### `final_code` - Исполненный код
**ЧТО**: Python код который выполнил AI
**КАК ПОКАЗЫВАТЬ**: В collapsible секции "Код" с подсветкой синтаксиса

## Рекомендации для UI

### Вариант 1: Разделенный интерфейс
```
┌─────────────────────────────────────┐
│ 📊 Результаты анализа               │ ← result_data (Markdown)
│                                     │
│ | Год | Сумма |                     │
│ |-----|-------|                     │
│ | 2019 | 1,234,567 |               │
│                                     │
│ 📈 График                           │ ← plots[0]
│ [график здесь]                      │
│                                     │
│ ▼ Логи выполнения (развернуть)     │ ← text_output (collapsible)
│ ▼ Код (развернуть)                 │ ← final_code (collapsible)
└─────────────────────────────────────┘
```

### Вариант 2: Вкладки
```
┌─────────────────────────────────────┐
│ [Результаты] [Логи] [Код] [Детали] │
│                                     │
│ (выбранная вкладка)                 │
└─────────────────────────────────────┘
```

## Пример React компонента

```tsx
interface AnalysisResult {
  success: boolean;
  result_data: string;     // Markdown
  text_output: string;     // Логи
  plots: string[];         // Base64 images
  final_code: string;      // Python code
}

function AnalysisView({ result }: { result: AnalysisResult }) {
  const [showLogs, setShowLogs] = useState(false);
  const [showCode, setShowCode] = useState(false);

  return (
    <div>
      {/* Основной результат */}
      <ReactMarkdown>{result.result_data}</ReactMarkdown>

      {/* Графики */}
      {result.plots.map((plot, i) => (
        <img key={i} src={plot} alt={`График ${i + 1}`} />
      ))}

      {/* Логи (collapsible) */}
      <details>
        <summary>🔍 Логи выполнения</summary>
        <pre className="logs">{result.text_output}</pre>
      </details>

      {/* Код (collapsible) */}
      <details>
        <summary>💻 Исполненный код</summary>
        <SyntaxHighlighter language="python">
          {result.final_code}
        </SyntaxHighlighter>
      </details>
    </div>
  );
}
```

## CSS для логов

```css
.logs {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  font-family: 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  overflow-x: auto;
}

/* Подсветка эмодзи шагов */
.logs::before {
  content: "";
}
```

## Важно!

⚠️ **text_output НЕ ТЕРЯЕТСЯ** - он всегда присутствует в ответе API
⚠️ **Фронтенд должен показывать** оба поля: `result_data` И `text_output`
✅ **result_data** - для пользователя (Markdown таблицы, графики)
✅ **text_output** - для понимания что делал AI (логи шагов)
