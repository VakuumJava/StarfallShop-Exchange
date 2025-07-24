# 🌟 StarfallShop Exchange - RUB to TON

Современное веб-приложение для обмена российских рублей на TON (Toncoin) с интеграцией TON Connect и WATA платежной системы.

## 🚀 Особенности

- 💎 **TON Connect Integration** - Подключение кошелька TON
- 💳 **WATA Payments** - Прием платежей в рублях
- 🎨 **Современный UI** - Дизайн в стиле Telegram Crypto Bot
- 📱 **Адаптивный дизайн** - Работает на всех устройствах
- ⚡ **Реальное время** - Живое обновление курсов и балансов
- 🔒 **Безопасность** - Защищенные API и валидация

## 🖥️ Демо

- **Frontend**: [https://yourusername.github.io/StarfallShop-Exchange](https://yourusername.github.io/StarfallShop-Exchange)
- **Backend API**: [https://starfallshop-backend-production.up.railway.app](https://starfallshop-backend-production.up.railway.app)

## 🛠️ Технологии

### Frontend
- HTML5, CSS3, JavaScript (ES6+)
- TON Connect UI
- Responsive Design
- CSS Animations & Gradients

### Backend
- Python 3.13+
- Flask + Flask-CORS
- Aiohttp для асинхронных запросов
- WATA API интеграция

## 📦 Установка и запуск

### Локальная разработка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/yourusername/StarfallShop-Exchange.git
cd StarfallShop-Exchange
```

2. **Установите зависимости**
```bash
pip install -r requirements.txt
```

3. **Создайте .env файл**
```env
WATA_TOKEN=your_wata_token_here
SERVICE_WALLET=UQAGUqc7XqO7Wc8tH7QGD8LuituUvdGUVccn-SphINODx7xa
TON_RATE_RUB=248.05
PORT=5001
DEBUG=True
```

4. **Запустите backend**
```bash
python backend.py
```

5. **Откройте frontend**
```bash
open index.html
```

## 🌐 Деплой

### GitHub Pages (Frontend)

1. Создайте репозиторий на GitHub
2. Загрузите файл `index.html`
3. Включите GitHub Pages в настройках репозитория
4. Ваш сайт будет доступен по адресу: `https://yourusername.github.io/repository-name`

### Railway (Backend)

1. Создайте аккаунт на [Railway](https://railway.app)
2. Подключите GitHub репозиторий
3. Добавьте переменные окружения:
   - `WATA_TOKEN`
   - `SERVICE_WALLET`
   - `TON_RATE_RUB`
4. Railway автоматически деплоит из `railway.json`

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `WATA_TOKEN` | API токен WATA платежной системы | - |
| `SERVICE_WALLET` | Адрес TON кошелька для отправки | - |
| `TON_RATE_RUB` | Курс обмена (RUB за 1 TON) | 248.05 |
| `PORT` | Порт для backend сервера | 5001 |
| `DEBUG` | Режим отладки | False |

### Frontend конфигурация

В `index.html` автоматически определяется окружение:
- **Локально**: `http://127.0.0.1:5001`
- **Production**: `https://starfallshop-backend-production.up.railway.app`

## 📱 Интеграция с Telegram

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен бота
3. Настройте Web App:
   - Команда: `/setmenubutton`
   - URL: ваш GitHub Pages URL
4. Добавьте кнопку меню с вашим приложением

## 🔧 API Endpoints

### GET `/`
Проверка состояния сервера
```json
{
  "status": "StarfallShop Exchange API is running",
  "version": "1.0.0",
  "ton_rate": 248.05
}
```

### GET `/ton-price`
Получение текущего курса
```json
{
  "price": 248.05
}
```

### POST `/create-payment`
Создание платежа
```json
{
  "rub_amount": 1000,
  "user_address": "TON_WALLET_ADDRESS"
}
```

### GET `/check-payment`
Проверка статуса платежа
```
/check-payment?id=PAYMENT_ID&order_id=ORDER_ID
```

## 🎨 Дизайн

Приложение выполнено в стиле Telegram Crypto Bot:
- 🌙 Темная тема с градиентами
- 💫 Анимации и эффекты
- 📱 Полная адаптивность
- 🎯 Интуитивный интерфейс

## 🔒 Безопасность

- ✅ CORS настроен для GitHub Pages
- ✅ Валидация входных данных
- ✅ Защищенные API ключи
- ✅ Обработка ошибок

## 📄 Лицензия

MIT License - используйте свободно для коммерческих и некоммерческих проектов.

## 🤝 Поддержка

- Telegram: [@StarfallShopRobot](https://t.me/StarfallShopRobot)
- Issues: [GitHub Issues](https://github.com/yourusername/StarfallShop-Exchange/issues)

## 🌟 Автор

Создано для @StarfallShopRobot с ❤️

---

**⚡ Готово к использованию! Просто деплойте и пользуйтесь!** 