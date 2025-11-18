# Промпт для Lovable: Отображение таблиц из AI CSV Agent

## Задача
Добавить поддержку отображения таблиц (DataFrame) из результатов API анализа CSV.

## Проблема
Сейчас когда агент возвращает таблицу, она отображается как "[object Object] • [object Object]" вместо нормальной HTML таблицы.

## Решение

### 1. Обновить логику обработки result_data

API теперь возвращает два типа данных в поле `result_data`:

**Обычные данные (числа, строки, списки):**
```json
{
  "result_data": 51666.666666666664
}
```

**Таблицы (DataFrame) - НОВЫЙ ФОРМАТ:**
```json
{
  "result_data": {
    "type": "dataframe",
    "data": [
      {"State": "ALABAMA", "Year": 1992, "Salary": 35000},
      {"State": "ALASKA", "Year": 1993, "Salary": 45000},
      {"State": "ARIZONA", "Year": 1994, "Salary": 38000}
    ],
    "columns": ["State", "Year", "Salary"],
    "shape": {"rows": 3, "columns": 3},
    "dtypes": {"State": "object", "Year": "int64", "Salary": "float64"}
  }
}
```

### 2. Код для React компонента

Добавь функцию для рендеринга result_data с проверкой типа:

```tsx
const renderResultData = (resultData: any) => {
  // Если нет данных
  if (!resultData) return null;

  // Проверяем, является ли это DataFrame
  if (resultData.type === "dataframe" && resultData.data) {
    const { data, columns, shape } = resultData;

    return (
      <div className="overflow-x-auto rounded-lg border border-gray-200 my-4">
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
          <p className="text-sm text-gray-600">
            📊 Таблица: {shape.rows} строк × {shape.columns} столбцов
          </p>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col: string, idx: number) => (
                <th
                  key={idx}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row: any, rowIdx: number) => (
              <tr key={rowIdx} className="hover:bg-gray-50">
                {columns.map((col: string, colIdx: number) => (
                  <td
                    key={colIdx}
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Если это обычный массив объектов (старый формат для обратной совместимости)
  if (Array.isArray(resultData) && resultData.length > 0 && typeof resultData[0] === 'object') {
    const columns = Object.keys(resultData[0]);

    return (
      <div className="overflow-x-auto rounded-lg border border-gray-200 my-4">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col: string, idx: number) => (
                <th
                  key={idx}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {resultData.map((row: any, rowIdx: number) => (
              <tr key={rowIdx} className="hover:bg-gray-50">
                {columns.map((col: string, colIdx: number) => (
                  <td
                    key={colIdx}
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Если это обычный массив чисел или строк
  if (Array.isArray(resultData)) {
    return (
      <div className="my-2">
        <p className="text-sm text-gray-600 mb-2">📊 Найденные элементы ({resultData.length}):</p>
        <ul className="list-disc list-inside space-y-1">
          {resultData.map((item: any, idx: number) => (
            <li key={idx} className="text-gray-800">{String(item)}</li>
          ))}
        </ul>
      </div>
    );
  }

  // Если это строка с переносами строк - конвертируем в список
  if (typeof resultData === 'string' && resultData.includes('\n')) {
    const lines = resultData.split('\n').filter(line => line.trim());
    if (lines.length > 1) {
      return (
        <div className="my-2">
          <p className="text-sm text-gray-600 mb-2">📊 Найденные элементы ({lines.length}):</p>
          <ul className="list-disc list-inside space-y-1">
            {lines.map((line: string, idx: number) => (
              <li key={idx} className="text-gray-800">{line.trim()}</li>
            ))}
          </ul>
        </div>
      );
    }
  }

  // Если это простое значение (число, строка, булево)
  if (typeof resultData === 'string' || typeof resultData === 'number' || typeof resultData === 'boolean') {
    return (
      <div className="my-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-lg font-semibold text-blue-900">{String(resultData)}</p>
      </div>
    );
  }

  // Для всех остальных случаев показываем JSON
  return (
    <pre className="my-2 p-3 bg-gray-50 rounded-lg text-sm overflow-x-auto">
      {JSON.stringify(resultData, null, 2)}
    </pre>
  );
};
```

### 3. Использование в компоненте

В компоненте сообщения замени текущий код отображения result_data на:

```tsx
{message.result_data && (
  <div className="mt-3">
    {renderResultData(message.result_data)}
  </div>
)}
```

### 4. Стили (если нужно добавить в tailwind.config)

```js
// Убедись что эти классы доступны:
// - overflow-x-auto
// - rounded-lg
// - border border-gray-200
// - divide-y divide-gray-200
// - hover:bg-gray-50
```

## Результат

После этих изменений:
- ✅ Таблицы будут отображаться как красивые HTML таблицы с заголовками
- ✅ Обычные данные (числа, строки) будут отображаться как раньше
- ✅ Массивы объектов (старый формат) также будут работать
- ✅ Добавлена информация о размере таблицы (строки × столбцы)
- ✅ Hover эффект на строках для лучшего UX

## Пример результата

Когда пользователь спросит "выведи таблицу первых 5 строк", он увидит:

```
📊 Таблица: 5 строк × 15 столбцов

┌──────────┬──────┬────────┬────────┐
│ State    │ Year │ Salary │ ...    │
├──────────┼──────┼────────┼────────┤
│ ALABAMA  │ 1992 │ 35000  │ ...    │
│ ALASKA   │ 1993 │ 45000  │ ...    │
│ ARIZONA  │ 1994 │ 38000  │ ...    │
│ ...      │ ...  │ ...    │ ...    │
└──────────┴──────┴────────┴────────┘
```

Вместо:
```
• [object Object]
• [object Object]
• [object Object]
```
