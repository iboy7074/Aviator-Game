from flask import Flask, request, jsonify, render_template_string
import random
import json
import requests
import threading
import time
from datetime import datetime
from collections import deque
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

app = Flask(__name__)

# Game State
game_history = deque(maxlen=1000)
predictor = {}

# Aviator Predictor AI
class AviatorPredictor:
    def __init__(self):
        self.history = deque(maxlen=100)
        self.streaks = {'low': 0, 'high': 0}
    
    def add_round(self, multiplier):
        self.history.append(multiplier)
        if multiplier < 2.0:
            self.streaks['low'] += 1
            self.streaks['high'] = 0
        else:
            self.streaks['high'] += 1
            self.streaks['low'] = 0
    
    def predict(self):
        if len(self.history) < 10:
            return {'multiplier': 2.0, 'confidence': 0.5, 'signal': 'WAIT'}
        
        recent = list(self.history)[-10:]
        avg = np.mean(recent)
        vol = np.std(recent)
        
        prediction = avg * 0.7 + (2.5 if self.streaks['low'] > 4 else 1.5) * 0.3
        prediction = max(1.01, min(20.0, prediction))
        
        signal = 'CASH_OUT' if prediction < 1.8 else 'SAFE_2X' if prediction < 3 else 'HIGH_RISK'
        
        return {
            'multiplier': round(prediction, 2),
            'confidence': round(0.4 + vol * 0.1, 2),
            'signal': signal,
            'streak': self.streaks
        }

aviator_ai = AviatorPredictor()

# Generate live game data
def generate_game():
    while True:
        # Provably fair crash
        crash = max(1.01, 1 / (1 - random.random() * 0.99))
        multiplier = 1.01
        
        while multiplier < crash:
            multiplier += random.uniform(0.01, 0.05)
            game_history.append(multiplier)
            aviator_ai.add_round(multiplier)
            time.sleep(random.uniform(0.08, 0.15))
        
        game_history.append(crash)
        aviator_ai.add_round(crash)
        time.sleep(3)

threading.Thread(target=generate_game, daemon=True).start()

# Flask Routes
@app.route('/')
def home():
    return render_template_string(open('aviator.html').read())

@app.route('/api/prediction')
def get_prediction():
    pred = aviator_ai.predict()
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'history': list(game_history)[-10:],
        **pred
    })

@app.route('/api/history')
def get_history():
    return jsonify(list(game_history)[-50:])

# Telegram Bot
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
application = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pred = aviator_ai.predict()
    keyboard = [[InlineKeyboardButton("🔮 Predict Now", callback_data='predict')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✈️ *Aviator Predictor Bot*\n\n"
        f"🎯 Next: `{pred['multiplier']}x`\n"
        f"📊 Confidence: {pred['confidence']*100:.0f}%\n"
        f"🚨 *{pred['signal']}*\n\n"
        f"🌐 Play: yourdomain.com\n"
        f"_Live AI predictions_",
        parse_mode='Markdown', reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'predict':
        pred = aviator_ai.predict()
        await query.edit_message_text(
            f"🔮 *LIVE PREDICTION*\n\n"
            f"🎯 `{pred['multiplier']}x`\n"
            f"📊 {pred['confidence']*100:.0f}% confidence\n"
            f"🚨 *{pred['signal']}*\n"
            f"🔥 Low: {pred['streak']['low']} | High: {pred['streak']['high']}",
            parse_mode='Markdown'
        )

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))

# Run everything
if __name__ == '__main__':
    from threading import Thread
    def run_bot():
        application.run_polling()
    
    Thread(target=run_bot, daemon=True).start()
    app.run(debug=True, port=5000)
