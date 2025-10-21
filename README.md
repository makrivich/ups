# Инструкция по запуску решения

P.S Ссылка на видеоматериал прикрепелнная в pdf-файле 2 части копируется не правильно (т.к в ссылке присутствует знак "-" и при копировании ссылки это воспринимается как перенос слова и не засчитывается), из-за этого прикрепляю ссылку сюда: [https://disk.yandex.ru/i/tzwHjFAWW5f3A ](https://disk.yandex.ru/i/tzwHjFA-WW5f3A). Надеюсь на ваше понимание
Это API для сервиса бронирования отелей и авиаперелетов.

## Требования

- Python 3.9 или выше
- pip (менеджер пакетов Python)

## Установка зависимостей

1. Скачайте или клонируйте репозиторий (если он доступен):
2. Установите необходимые пакеты, выполнив команду в терминале:
   ```
   pip install fastapi uvicorn sqlalchemy pydantic passlib python-jose[cryptography] python-multipart
   ```

## Настройка базы данных

1. База данных `booking.db` будет создана автоматически при первом запуске сервера.


## Запуск сервера

1. Откройте терминал и перейдите в директорию с файлом `main.py`:
   ```
   cd /путь/к/вашей/папке
   ```

2. Запустите сервер с помощью uvicorn:
   ```
   uvicorn main:app --reload
   ```
   - Сервер будет доступен по адресу `http://127.0.0.1:8000`.

## Доступ к документации

- После запуска сервера откройте в браузере `http://127.0.0.1:8000/docs`, чтобы увидеть  документацию API (Swagger UI).

## Примеры команд

Ниже приведены примеры команд `curl` для базового взаимодействия с API. Убедитесь, что сервер запущен перед выполнением. Замените `<your_token>` на токен, полученный через `/token`. 
Токены авторизации имеют ограниченный срок действия. Если авторизация не работает, получите новый токен через `/token`.

### Регистрация пользователя
```
curl -X POST "http://127.0.0.1:8000/register" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"email\": \"user@example.com\", \"name\": \"John Doe\", \"password\": \"password123\", \"role\": \"user\"}"
```

### Получение токена для авторизации
```
curl -X POST "http://127.0.0.1:8000/token" -H "accept: application/json" -H "Content-Type: application/x-www-form-urlencoded" -d "username=user@example.com&password=password123"
```
- Ответ будет содержать `access_token`, который нужно использовать в последующих запросах в заголовке `Authorization: Bearer <your_token>`.

### Создание отеля (требуется роль admin)
```
curl -X POST "http://127.0.0.1:8000/hotels" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"name\": \"Luxury Hotel\", \"city\": \"Paris\", \"stars\": 5}"
```

### Получение списка отелей
```
curl -X GET "http://127.0.0.1:8000/hotels?city=Paris&order_by_stars=desc" -H "accept: application/json" -H "Authorization: Bearer <your_token>"
```

### Создание комнаты (требуется роль admin)
```
curl -X POST "http://127.0.0.1:8000/rooms" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"hotel_id\": 1, \"type\": \"Double\", \"rooms_count\": 10, \"price\": 150.0, \"capacity\": 2}"
```

### Получение доступных комнат
```
curl -X GET "http://127.0.0.1:8000/available_rooms?check_in=2025-10-25T10:00:00&check_out=2025-10-26T10:00:00&hotel_id=1&order_by_price=asc" -H "accept: application/json" -H "Authorization: Bearer <your_token>"
```

### Бронирование комнаты по датам
```
curl -X POST "http://127.0.0.1:8000/bookings/by_dates" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"room_id\": 1, \"check_in\": \"2025-10-25T10:00:00\", \"check_out\": \"2025-10-26T10:00:00\"}"
```

### Бронирование комнаты на количество дней
```
curl -X POST "http://127.0.0.1:8000/bookings/by_days?room_id=1&check_in=2025-10-25T10:00:00&days=2" -H "accept: application/json" -H "Authorization: Bearer <your_token>"
```

### Отмена бронирования
```
curl -X DELETE "http://127.0.0.1:8000/bookings/1" -H "accept: application/json" -H "Authorization: Bearer <your_token>"
```

### Создание рейса (требуется роль admin)
```
curl -X POST "http://127.0.0.1:8000/flights" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"departure_city\": \"Moscow\", \"arrival_city\": \"London\", \"departure_time\": \"2025-10-25T09:00:00\", \"arrival_time\": \"2025-10-25T11:00:00\", \"price\": 200.0, \"total_seats\": 100}"
```

### Получение списка рейсов
```
curl -X GET "http://127.0.0.1:8000/flights" -H "accept: application/json" -H "Authorization: Bearer <your_token>"
```

### Поиск билетов (Москва → Лондон, сортировка по времени)
```
curl -X POST "http://127.0.0.1:8000/flights/search?order_by_time=time_asc" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"from_city\": \"Moscow\", \"to_city\": \"London\", \"date_from\": \"2025-10-25T00:00:00\", \"date_to\": \"2025-10-25T23:59:59\", \"passengers\": 1}"
```

### Бронирование рейса
```
curl -X POST "http://127.0.0.1:8000/flights/book/1?passengers=1" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{}"
```

### Обновление данных пользователя
```
curl -X PUT "http://127.0.0.1:8000/user/update" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer <your_token>" -d "{\"name\": \"John Smith\"}"
```

### Удаление отеля (требуется роль admin)
```
curl -X DELETE "http://127.0.0.1:8000/hotels/1" -H "accept: application/json" -H "Authorization: Bearer <your_token>"
```

P.P.S Если возникают ошибки, проверьте логи терминала, где запущен сервер, и убедитесь, что все зависимости установлены.
