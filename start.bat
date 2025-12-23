@echo off
echo Starting Draft Helper API...
:: Активируем виртуальное окружение
call venv\Scripts\activate
:: Запускаем сервер
python -m uvicorn main:app --reload
pause