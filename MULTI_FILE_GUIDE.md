# Руководство по работе с несколькими CSV файлами

## Что нового

### 1. Агент теперь **объясняет** что делает

Вместо сухих цифр агент:
- Объясняет какой анализ выполняет (1-2 предложения)
- Анализирует полученные результаты
- Делает выводы и находит интересные паттерны

**Пример запроса:**
```
Какая средняя зарплата по штатам?
```

**Ответ агента:**
```
Анализирую данные о зарплатах по 51 штату...

Средняя зарплата по всем штатам: $51,667

Интересно: самая высокая средняя зарплата в CALIFORNIA ($68,500),
а самая низкая в MISSISSIPPI ($42,300). Разница составляет $26,200 (38%).
```

### 2. Поддержка множественных CSV файлов

Теперь можно загрузить **несколько файлов** одновременно и делать перекрестный анализ!

## API Endpoints

### Один файл (как раньше)
```
POST /api/analyze
```

### Несколько файлов (новое!)
```
POST /api/analyze-multi
```

## Примеры использования

### Пример 1: Два файла - заказы и клиенты

**Файлы:**
- `orders.csv` - данные о заказах (order_id, customer_id, amount, date)
- `customers.csv` - данные о клиентах (customer_id, name, region)

**Запрос:**
```
Соедини таблицы заказов и клиентов, покажи топ-10 клиентов по общей сумме заказов
```

**Что делает агент:**
```python
print("Объединяю таблицы заказов (orders) и клиентов (customers) по customer_id...")

# Доступны переменные: df (orders), customers
merged = df.merge(customers, on='customer_id')
top_customers = merged.groupby('name')['amount'].sum().sort_values(ascending=False).head(10)

print(f"Найдено {len(merged)} заказов от {merged['customer_id'].nunique()} уникальных клиентов")
print("Топ клиент потратил ${:,.2f}, что в 3 раза больше среднего".format(top_customers.iloc[0]))

result = top_customers.reset_index()
result.columns = ['Клиент', 'Общая сумма заказов']
```

### Пример 2: Три файла - продажи, продукты, категории

**Файлы:**
- `sales.csv` - продажи (sale_id, product_id, quantity, price)
- `products.csv` - продукты (product_id, name, category_id)
- `categories.csv` - категории (category_id, category_name)

**Запрос:**
```
Покажи топ-5 категорий по выручке и построй график
```

**Что делает агент:**
```python
print("Анализирую продажи по категориям...")
print(f"Доступны таблицы: sales ({df.shape[0]} записей), products ({products.shape[0]} товаров), categories ({categories.shape[0]} категорий)")

# Объединяем все три таблицы
merged = df.merge(products, on='product_id').merge(categories, on='category_id')
merged['revenue'] = merged['quantity'] * merged['price']

category_revenue = merged.groupby('category_name')['revenue'].sum().sort_values(ascending=False).head(5)

print(f"Всего выручка: ${category_revenue.sum():,.2f}")
print(f"Топ категория '{category_revenue.index[0]}' принесла ${category_revenue.iloc[0]:,.2f} ({category_revenue.iloc[0]/category_revenue.sum()*100:.1f}%)")

# График
plt.figure(figsize=(10, 6))
category_revenue.plot(kind='bar')
plt.title('Топ-5 категорий по выручке')
plt.xlabel('Категория')
plt.ylabel('Выручка ($)')
plt.xticks(rotation=45)
plt.tight_layout()

result = category_revenue.reset_index()
result.columns = ['Категория', 'Выручка']
```

## Как это работает в коде

### Доступные переменные в Python

Когда загружено несколько файлов, агент автоматически получает доступ к ним:

**1 файл:**
- `df` - основной DataFrame

**2 файла** (orders.csv, customers.csv):
- `df` - orders (первый файл)
- `orders` - orders
- `customers` - customers

**3+ файла** (sales.csv, products.csv, categories.csv):
- `df` - sales (первый файл)
- `sales` - sales
- `products` - products
- `categories` - categories

## Интеграция с Lovable

### Для одного файла (существующий код)

Используй endpoint `/api/analyze` как раньше:

```tsx
const formData = new FormData();
formData.append('file', file);
formData.append('query', userQuery);
formData.append('chat_history', JSON.stringify(chatHistory));

const response = await fetch('https://julius.sopods.store/api/analyze', {
  method: 'POST',
  body: formData
});
```

### Для нескольких файлов (новое!)

Используй endpoint `/api/analyze-multi`:

```tsx
const formData = new FormData();

// Добавляем несколько файлов
files.forEach(file => {
  formData.append('files', file);
});

formData.append('query', userQuery);
formData.append('chat_history', JSON.stringify(chatHistory));

const response = await fetch('https://julius.sopods.store/api/analyze-multi', {
  method: 'POST',
  body: formData
});
```

### Пример React компонента для загрузки файлов

```tsx
const MultiFileUpload = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleAnalyze = async () => {
    const formData = new FormData();

    files.forEach(file => {
      formData.append('files', file);
    });

    formData.append('query', query);

    const response = await fetch('https://julius.sopods.store/api/analyze-multi', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    setResult(data);
  };

  return (
    <div>
      <input
        type="file"
        multiple
        accept=".csv"
        onChange={handleFileChange}
      />

      {files.length > 0 && (
        <div>
          <p>Загружено файлов: {files.length}</p>
          <ul>
            {files.map((file, idx) => (
              <li key={idx}>{file.name}</li>
            ))}
          </ul>
        </div>
      )}

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ваш запрос..."
      />

      <button onClick={handleAnalyze}>
        Анализировать
      </button>

      {result && (
        <div>
          {/* Отображение результата как обычно */}
          {result.text_output && <p>{result.text_output}</p>}
          {result.result_data && renderResultData(result.result_data)}
          {result.plots?.map((plot, idx) => (
            <img key={idx} src={plot} alt="График" />
          ))}
        </div>
      )}
    </div>
  );
};
```

## Типичные запросы для нескольких файлов

### JOIN таблиц
```
Соедини заказы и клиентов по customer_id
```

### Агрегация по категориям
```
Покажи общую выручку по категориям продуктов
```

### Анализ связей
```
Какие клиенты из региона 'North' покупали товары категории 'Electronics'?
```

### Сложная аналитика
```
Построй воронку продаж: сколько клиентов посетили сайт, добавили товар в корзину и совершили покупку
```

### Временной анализ
```
Сравни продажи по месяцам для топ-3 категорий товаров
```

## Ответы API

Формат ответа такой же, но добавлено поле `files_info`:

```json
{
  "success": true,
  "text_output": "Анализирую данные...\nНайдено 100 заказов от 25 клиентов...",
  "result_data": {
    "type": "dataframe",
    "data": [...],
    "columns": ["Клиент", "Сумма"],
    "shape": {"rows": 10, "columns": 2}
  },
  "plots": ["data:image/png;base64,..."],
  "files_info": {
    "orders": {
      "filename": "orders.csv",
      "rows": 100,
      "columns": 4,
      "column_names": ["order_id", "customer_id", "amount", "date"]
    },
    "customers": {
      "filename": "customers.csv",
      "rows": 25,
      "columns": 3,
      "column_names": ["customer_id", "name", "region"]
    }
  }
}
```

## Ограничения

- Максимум файлов: нет жесткого лимита, но рекомендуется до 5 файлов
- Размер файлов: суммарно до 50MB (настраивается в FastAPI)
- Все файлы должны быть в формате CSV

## Примеры из реального мира

### E-commerce
```
Файлы: orders.csv, customers.csv, products.csv
Запрос: "Покажи RFM-анализ клиентов (Recency, Frequency, Monetary)"
```

### Финансы
```
Файлы: transactions.csv, accounts.csv, categories.csv
Запрос: "Построй отчет о доходах и расходах по категориям за последний квартал"
```

### HR аналитика
```
Файлы: employees.csv, departments.csv, salaries.csv
Запрос: "Сравни среднюю зарплату по отделам с учетом стажа работы"
```
