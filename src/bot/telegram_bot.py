from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from config.config import Config
from src.database.connection import DatabaseManager
from src.utils.logger import activity_logger, error_logger
from src.database.models import User, UserRole
from src.api.price_service import PriceService
import asyncio
import io
import matplotlib.pyplot as mpf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

class TradingBot:
    def __init__(self, db_session=None):
        self.db = DatabaseManager()
        self.price_service = PriceService()
        self.price_alerts = {}  # {user_id: {symbol: {price: float, condition: 'above'|'below'}}}
        
        # Initialize application
        self.app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            session = next(self.db.get_session())
            
            # Check if user exists
            db_user = session.query(User).filter_by(telegram_id=str(user.id)).first()
            if not db_user:
                db_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    role=UserRole.FREE
                )
                session.add(db_user)
                session.commit()
            
            keyboard = [
                [
                    InlineKeyboardButton("Cek Harga 💰", callback_data='price'),
                    InlineKeyboardButton("Status Bot 🤖", callback_data='status')
                ],
                [
                    InlineKeyboardButton("Bantuan ❓", callback_data='help')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Selamat datang {user.first_name}! Saya adalah asisten trading crypto anda.\n"
                "Pilih opsi di bawah ini:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            error_logger.error(f"Error in start command: {str(e)}")
            await update.message.reply_text("Maaf, terjadi kesalahan. Silakan coba lagi nanti.")
        finally:
            session.close()
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 *Perintah yang Tersedia:*\n\n"
            "/start - Mulai bot\n"
            "/help - Tampilkan pesan bantuan ini\n"
            "/price - Cek harga cryptocurrency\n"
            "/status - Cek status bot\n"
            "/pairs - Cek pasangan trading yang tersedia\n"
            "/chart - Lihat grafik cryptocurrency\n\n"
            "Untuk masalah teknis, silakan hubungi support."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle perintah /price"""
        try:
            if context.args:
                symbol = context.args[0].upper()
                exchange = context.args[1].lower() if len(context.args) > 1 else None
                
                prices = self.price_service.get_price(symbol, exchange)
                message = self.price_service.format_price_message(prices)
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                keyboard = [
                    [
                        InlineKeyboardButton("BTC (Semua)", callback_data='price_BTC_all'),
                        InlineKeyboardButton("ETH (Semua)", callback_data='price_ETH_all')
                    ],
                    [
                        InlineKeyboardButton("BTC (Indodax)", callback_data='price_BTC_indodax'),
                        InlineKeyboardButton("BTC (Bitget)", callback_data='price_BTC_bitget')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "Pilih pasangan trading atau gunakan:\n"
                    "/price <simbol> [exchange]\n"
                    "Contoh: /price btc atau /price btc indodax",
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            error_logger.error(f"Error pada perintah price: {str(e)}")
            await update.message.reply_text("Maaf, tidak bisa mengambil harga. Silakan coba lagi nanti.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menangani perintah /status"""
        try:
            ticker = self.price_service.get_ticker("BTC/USDT")
            ws_status = "Terhubung" if self.price_service.ws_connected else "Terputus"
            
            status_text = (
                "🤖 *Status Bot*\n\n"
                f"Koneksi Exchange: ✅\n"
                f"Status WebSocket: {ws_status}\n"
                f"Pembaruan Harga Terakhir: {ticker['timestamp']}\n"
                f"Versi Bot: 1.0.0"
            )
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            error_logger.error(f"Error pada perintah status: {str(e)}")
            await update.message.reply_text("❌ Beberapa layanan sedang tidak tersedia.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data.startswith('price_'):
                symbol = query.data.replace('price_', '')
                ticker_data = self.price_service.get_public_ticker(symbol)
                
                if ticker_data:
                    # Format angka untuk tampilan yang lebih baik
                    last_price = f"${ticker_data['last']:,.2f}"
                    high_price = f"${ticker_data['high']:,.2f}"
                    low_price = f"${ticker_data['low']:,.2f}"
                    volume = f"{ticker_data['baseVolume']:.2f}"
                    change = f"{ticker_data['percentage']:+.2f}"
                    
                    price_text = (
                        f"💰 *{symbol[:3]}/{symbol[3:]}*\n\n"
                        f"Harga: {last_price}\n"
                        f"24j Tertinggi: {high_price}\n"
                        f"24j Terendah: {low_price}\n"
                        f"Volume 24j: {volume} {symbol[:3]}\n"
                        f"Perubahan 24j: {change}%"
                    )
                    
                    await query.edit_message_text(price_text, parse_mode='Markdown')
                else:
                    await query.edit_message_text(f"❌ Could not find price for {symbol}")
                    
            elif query.data in ['help', 'status']:
                if query.data == 'help':
                    await self.help_command(update, context)
                else:
                    await self.status_command(update, context)
                    
        except Exception as e:
            error_logger.error(f"Error in button callback: {str(e)}")
            await query.edit_message_text("Sorry, an error occurred. Please try again.")
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command for basic market analysis"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("BTC/USDT", callback_data='analyze_BTCUSDT'),
                    InlineKeyboardButton("ETH/USDT", callback_data='analyze_ETHUSDT')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Select a pair to analyze:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            error_logger.error(f"Error in analyze command: {str(e)}")
            await update.message.reply_text("Sorry, analysis is currently unavailable.")
    
    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        try:
            user = update.effective_user
            session = next(self.db.get_session())
            
            # Get user's trades
            trades = session.query(Trade).filter_by(
                user_id=user.id,
                status='open'
            ).all()
            
            if not trades:
                await update.message.reply_text(
                    "Anda tidak memiliki posisi terbuka.\n"
                    "Gunakan /trade untuk mulai trading!"
                )
                return
            
            portfolio_text = "📊 *Portofolio Anda*\n\n"
            total_pnl = 0
            
            for trade in trades:
                current_price = self.price_service.get_ticker(trade.symbol)['last']
                pnl = (current_price - trade.entry_price) * trade.quantity
                if trade.direction == 'short':
                    pnl = -pnl
                
                total_pnl += pnl
                portfolio_text += (
                    f"*{trade.symbol}*\n"
                    f"Direction: {trade.direction.upper()}\n"
                    f"Entry: ${trade.entry_price:.2f}\n"
                    f"Current: ${current_price:.2f}\n"
                    f"PnL: ${pnl:.2f}\n\n"
                )
            
            portfolio_text += f"*Total PnL: ${total_pnl:.2f}*"
            
            await update.message.reply_text(portfolio_text, parse_mode='Markdown')
            
        except Exception as e:
            error_logger.error(f"Error in portfolio command: {str(e)}")
            await update.message.reply_text("Sorry, couldn't fetch portfolio data.")
        finally:
            session.close()
    
    async def alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menangani perintah /alert untuk notifikasi harga"""
        try:
            if len(context.args) != 3:
                await update.message.reply_text(
                    "Penggunaan: /alert SIMBOL HARGA KONDISI\n"
                    "Contoh: /alert BTCUSDT 50000 diatas"
                )
                return
            
            symbol, price, condition = context.args
            price = float(price)
            
            if condition not in ['diatas', 'dibawah']:
                await update.message.reply_text("Kondisi harus 'diatas' atau 'dibawah'")
                return
            
            user_id = update.effective_user.id
            if user_id not in self.price_alerts:
                self.price_alerts[user_id] = {}
            
            self.price_alerts[user_id][symbol] = {
                'price': price,
                'condition': condition
            }
            
            await update.message.reply_text(
                f"Notifikasi diatur untuk {symbol} ketika harga {condition} Rp {price:,.0f}"
            )
            
        except ValueError:
            await update.message.reply_text("Nilai harga tidak valid")
        except Exception as e:
            error_logger.error(f"Error pada perintah alert: {str(e)}")
            await update.message.reply_text("Maaf, tidak bisa mengatur notifikasi.")
    
    async def sentiment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sentiment command for market sentiment analysis"""
        try:
            symbol = "BTC/USDT"  # Default to BTC
            if context.args:
                symbol = context.args[0]
            
            # Get recent OHLCV data
            ohlcv = self.price_service.get_ohlcv(symbol, timeframe='1h', limit=24)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calculate basic indicators
            df['returns'] = df['close'].pct_change()
            df['volatility'] = df['returns'].rolling(6).std()
            
            # Simple sentiment analysis
            price_change_24h = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
            volume_change = ((df['volume'].iloc[-1] - df['volume'].mean()) / df['volume'].mean()) * 100
            volatility = df['volatility'].iloc[-1]
            
            # Determine sentiment
            sentiment_score = 0
            sentiment_score += 1 if price_change_24h > 0 else -1
            sentiment_score += 1 if volume_change > 20 else (-1 if volume_change < -20 else 0)
            sentiment_score += -1 if volatility > df['volatility'].mean() * 1.5 else 0
            
            sentiment = "Bullish 🟢" if sentiment_score > 0 else "Bearish 🔴" if sentiment_score < 0 else "Netral ⚪"
            
            sentiment_text = (
                f"📊 *Analisis Sentimen Pasar {symbol}*\n\n"
                f"Sentimen Saat Ini: {sentiment}\n"
                f"Perubahan Harga 24j: {price_change_24h:.2f}%\n"
                f"Perubahan Volume: {volume_change:.2f}%\n"
                f"Volatilitas: {volatility:.4f}\n\n"
                f"Analisis berdasarkan pergerakan harga, volume, dan volatilitas."
            )
            
            await update.message.reply_text(sentiment_text, parse_mode='Markdown')
            
        except Exception as e:
            error_logger.error(f"Error in sentiment command: {str(e)}")
            await update.message.reply_text("Sorry, couldn't analyze market sentiment.")
    
    async def check_alerts(self, context: ContextTypes.DEFAULT_TYPE):
        """Background task to check price alerts"""
        while True:
            try:
                for user_id, alerts in self.price_alerts.items():
                    for symbol, alert in alerts.items():
                        current_price = self.price_service.get_ticker(symbol)['last']
                        
                        alert_triggered = (
                            (alert['condition'] == 'above' and current_price > alert['price']) or
                            (alert['condition'] == 'below' and current_price < alert['price'])
                        )
                        
                        if alert_triggered:
                            alert_text = (
                                f"🚨 *Price Alert*\n\n"
                                f"{symbol} is now {alert['condition']} ${alert['price']}\n"
                                f"Current price: ${current_price}"
                            )
                            
                            # Send alert to user using application instead of bot
                            await self.app.bot.send_message(
                                chat_id=user_id,
                                text=alert_text,
                                parse_mode='Markdown'
                            )
                            
                            # Remove triggered alert
                            del self.price_alerts[user_id][symbol]
                            
            except Exception as e:
                error_logger.error(f"Error checking alerts: {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def pairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pairs command"""
        try:
            exchange = context.args[0].lower() if context.args else None
            pairs = self.price_service.get_available_pairs(exchange)
            message = self.price_service.format_pairs_message(pairs)
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            error_logger.error(f"Error in pairs command: {str(e)}")
            await update.message.reply_text("Sorry, couldn't fetch available pairs.")
    
    async def chart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menangani perintah /chart"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Penggunaan: /chart <simbol> [timeframe] [exchange]\n"
                    "Contoh: /chart btc 15m indodax\n\n"
                    "Timeframe yang didukung:\n"
                    "- 1m, 5m, 15m, 1h, 4h, 1d\n\n"
                    "Exchange yang didukung:\n"
                    "- indodax\n"
                    "- bitget"
                )
                return
            
            symbol = context.args[0].upper()
            timeframe = context.args[1] if len(context.args) > 1 else "15m"
            exchange = context.args[2].lower() if len(context.args) > 2 else "indodax"

            if exchange not in ["indodax", "bitget"]:
                await update.message.reply_text("❌ Exchange tidak didukung. Gunakan 'indodax' atau 'bitget'")
                return

            progress_msg = await update.message.reply_text("📊 Mengambil data dan membuat grafik...")

            # Get OHLCV data with error handling
            ohlcv = self.price_service.get_ohlcv(symbol, timeframe, exchange)
            if not ohlcv or len(ohlcv) < 2:
                await progress_msg.edit_text(
                    "❌ Tidak dapat mengambil data chart.\n"
                    "Pastikan:\n"
                    "- Simbol valid (contoh: BTC, ETH)\n"
                    "- Timeframe didukung (1m, 5m, 15m, 1h, 4h, 1d)\n"
                    "- Exchange didukung dan tersedia"
                )
                return

            # Convert to DataFrame with better error handling
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Calculate width for bars based on time difference
            if len(df) > 1:
                time_diff = (df.index[1] - df.index[0]).total_seconds()
                bar_width = 0.8 * time_diff / 86400  # Convert to days for matplotlib
            else:
                bar_width = 0.8  # Default width if only one data point

            # Create figure with dark theme
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(12, 8))
            fig.patch.set_facecolor('#1e222d')

            # Create subplots with specific ratios
            gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.1)
            ax1 = fig.add_subplot(gs[0])
            ax2 = fig.add_subplot(gs[1], sharex=ax1)

            # Calculate colors for volume bars
            volume_colors = np.where(df.close >= df.open, '#26a69a', '#ef5350')

            # Plot candlesticks and volume with the calculated bar_width
            plot_candlestick(ax1, df)
            ax2.bar(df.index, df.volume, color=volume_colors, alpha=0.5, width=bar_width)  # Fixed: using bar_width instead of width

            # Calculate price change for title
            price_change = df['close'].iloc[-1] - df['close'].iloc[0]
            price_change_pct = (price_change / df['close'].iloc[0]) * 100

            # Style improvements
            for ax in [ax1, ax2]:
                ax.set_facecolor('#1e222d')
                ax.grid(True, color='#2a2e39', linestyle='--', alpha=0.3)
                ax.tick_params(axis='both', colors='#787b86', labelsize=9)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                for spine in ax.spines.values():
                    spine.set_color('#2a2e39')

            # Add custom title with OHLCV info
            title = (
                f"{symbol}/IDR • {timeframe} • {exchange.upper()}\n"
                f"O: {df['open'].iloc[-1]:,.0f}  "
                f"H: {df['high'].iloc[-1]:,.0f}  "
                f"L: {df['low'].iloc[-1]:,.0f}  "
                f"C: {df['close'].iloc[-1]:,.0f}  "
                f"({price_change_pct:+.2f}%)"
            )
            ax1.set_title(title, color='#787b86', pad=10)

            # Save chart with high quality
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor='#1e222d', edgecolor='none')
            buf.seek(0)

            # Send chart and cleanup
            await progress_msg.delete()
            await update.message.reply_photo(
                photo=buf,
                caption=f"📊 {symbol}/IDR {timeframe} Chart dari {exchange.upper()}"
            )
            plt.close()

        except Exception as e:
            error_logger.error(f"Error dalam chart command: {str(e)}", exc_info=True)
            await update.message.reply_text(
                "❌ Terjadi kesalahan saat membuat grafik.\n"
                "Mohon coba lagi nanti."
            )
    
    async def initialize(self):
        """Initialize bot handlers"""
        try:
            activity_logger.info("Initializing bot handlers...")
            
            # Verify bot token
            me = await self.app.bot.get_me()
            activity_logger.info(f"Bot connected as: {me.first_name} (@{me.username})")
            
            # Add handlers
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("price", self.price_command))
            self.app.add_handler(CommandHandler("status", self.status_command))
            self.app.add_handler(CommandHandler("analyze", self.analyze_command))
            self.app.add_handler(CommandHandler("portfolio", self.portfolio_command))
            self.app.add_handler(CommandHandler("alert", self.alert_command))
            self.app.add_handler(CommandHandler("sentiment", self.sentiment_command))
            self.app.add_handler(CommandHandler("pairs", self.pairs_command))
            self.app.add_handler(CommandHandler("chart", self.chart_command))
            self.app.add_handler(CallbackQueryHandler(self.button_callback))
            
            # Start background tasks
            self.app.job_queue.run_repeating(self.check_alerts, interval=60)
            
            activity_logger.info("Bot handlers initialized successfully")
        except Exception as e:
            error_logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise
    
    async def run(self):
        """Start the bot"""
        try:
            # Initialize bot
            await self.initialize()
            activity_logger.info("Starting bot polling...")
            
            # Start the application
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            activity_logger.info("Bot is running...")
            
            # Keep the bot running
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                activity_logger.info("Received cancel signal")
            except KeyboardInterrupt:
                activity_logger.info("Received keyboard interrupt")
            
        except Exception as e:
            error_logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
            raise
        finally:
            activity_logger.info("Stopping bot...")
            try:
                if hasattr(self.app.updater, 'running') and self.app.updater.running:
                    await self.app.updater.stop()
                if hasattr(self.app, 'running') and self.app.running:
                    await self.app.stop()
            except Exception as e:
                error_logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

def plot_candlestick(ax, df):
    """Plot candlesticks in TradingView style"""
    # Calculate bar width based on data frequency
    time_deltas = df.index[1:] - df.index[:-1]
    avg_delta = pd.Timedelta(time_deltas.mean())
    width = avg_delta * 0.8  # 80% of time interval
    
    for idx, row in df.iterrows():
        # Determine color based on price movement
        color = '#26a69a' if row.close >= row.open else '#ef5350'
        
        # Plot candle body
        body_bottom = min(row.open, row.close)
        body_top = max(row.open, row.close)
        body_height = body_top - body_bottom
        
        # Plot body
        rect = plt.Rectangle(
            xy=(idx - width/2, body_bottom),
            width=width,
            height=body_height,
            facecolor=color,
            edgecolor=color,
            alpha=1,
            zorder=3
        )
        ax.add_patch(rect)
        
        # Plot wicks
        ax.plot(
            [idx, idx],
            [row.low, body_bottom],
            color=color,
            linewidth=1,
            zorder=2
        )
        ax.plot(
            [idx, idx],
            [body_top, row.high],
            color=color,
            linewidth=1,
            zorder=2
        )