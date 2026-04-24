UI_WIDGETS = {
    # 0. ПРОСТОЙ ТЕСТ / ОПИСАНИЕ (Базовый компонент)
    "RichText": {
        "description": "Используй для кратких ответов, описаний.",
        "schema": {
            "content": "string"
        }
    },
    # 1. ТАБЛИЦА (Универсальная)
    "DataGrid": {
        "description": "Если данные нужно вывести по категориям в виде таблицы, структурировать данные",
        "schema": {
            "columns": "string[] (например, ['Параметр', 'Значение', 'Комментарий'])",
            "rows": "object[] (массив объектов, ключи которых соответствуют columns)"
        }
    },

    # 2. ГРАФИКИ (Три вида под разные задачи)
    "BarChart": {
        "description": "Сравнение величин между разными категориями, если нужно изобразить график.",
        "schema": { "title": "string", "unit": "string", "data": "[{name: string, value: number}]" }
    },
    "LineChart": {
        "description": "Отображение динамики изменений во времени, если нужно изобразить график",
        "schema": { "title": "string", "unit": "string", "data": "[{name: string, value: number}]" }
    },
    "PieChart": {
        "description": "Процентное соотношение частей в целом, если нужно изобразить график.",
        "schema": { "title": "string", "data": "[{name: string, value: number}]" }
    },

    # 3. ТЕСТЫ (С разной логикой ответов)
    "Quiz": {
        "description": "Проверка знаний пользователя по прочитанному тексту, составить тест.",
        "schema": {
            "title": "string",
            "questions": [
                {
                    "type": "single | multiple", # Тип вопроса: 1 правильный или несколько
                    "question": "string",
                    "options": "string[]",
                    "correctAnswers": "string[] (массив букв/значений)",
                    "explanation": "string (почему этот выбор верный)"
                }
            ]
        }
    }
}