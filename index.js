require('dotenv').config();
const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const { Kazagumo } = require('kazagumo');
const { Connectors } = require('shoukaku');
const express = require('express');

// ==========================================
// 1. HỆ THỐNG ANTI-CRASH (BẢO VỆ BOT 100%)
// ==========================================
process.on('unhandledRejection', (reason, promise) => {
    console.error('⚠️ [ANTI-CRASH] Bỏ qua lỗi Promise:', reason);
});
process.on('uncaughtException', (error) => {
    console.error('⚠️ [ANTI-CRASH] Bỏ qua lỗi hệ thống:', error);
});
process.on('uncaughtExceptionMonitor', (error, origin) => {
    console.error('⚠️ [ANTI-CRASH] Giám sát lỗi:', error, origin);
});

// ==========================================
// 2. WEB SERVER & DISCORD CLIENT
// ==========================================
const app = express();
app.get('/', (req, res) => res.send('Bot Node.js đang hoạt động với Anti-Crash!'));
const PORT = process.env.PORT || 8080;
app.listen(PORT, '0.0.0.0', () => console.log(`🌐 Web server port ${PORT}`));

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
    ]
});

// ==========================================
// 3. CỤM MÁY CHỦ LAVALINK V4 (KẾT NỐI BẢO MẬT SSL)
// Chỉ giữ lại Node hoạt động tốt nhất để tránh spam log
// ==========================================
const Nodes = [
    {
        name: 'Ajie_V4_SSL',
        url: 'lava-v4.ajieblogs.eu.org:443',
        auth: 'https://dsc.gg/ajidevserver',
        secure: true
    }
];

client.manager = new Kazagumo({
    defaultSearchEngine: "youtube",
    send: (guildId, payload) => {
        const guild = client.guilds.cache.get(guildId);
        if (guild) guild.shard.send(payload);
    }
}, new Connectors.DiscordJS(client), Nodes);

client.manager.shoukaku.on('ready', (name) => console.log(`✅ Lavalink Node: ${name} đã kết nối thành công!`));
client.manager.shoukaku.on('error', (name, error) => console.error(`❌ Lỗi Lavalink (${name}): Node đang quá tải hoặc offline.`));
client.manager.on('playerEmpty', player => player.destroy());

// ==========================================
// 4. LỆNH SLASH & XỬ LÝ SỰ KIỆN TỰ BẢO VỆ
// ==========================================
const commands = [
    {
        name: 'play',
        description: 'Phát nhạc từ YouTube, Spotify, SoundCloud...',
        options: [{ name: 'query', type: 3, description: 'Tên bài hát hoặc URL', required: true }]
    },
    { name: 'skip', description: 'Bỏ qua bài hiện tại' },
    { name: 'stop', description: 'Dừng nhạc và thoát' }
];

client.once('ready', async () => {
    console.log(`🎉 Bot đã online: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(Routes.applicationCommands(client.user.id), { body: commands });
        console.log('✅ Đã đồng bộ lệnh Slash!');
    } catch (e) { console.error('Lỗi đồng bộ lệnh:', e); }
});

client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    // Bọc toàn bộ quá trình xử lý lệnh vào Try/Catch
    try {
        if (interaction.commandName === 'play') {
            const query = interaction.options.getString('query');
            const { channel } = interaction.member.voice;
            
            if (!channel) return interaction.reply({ content: '❌ Bạn cần vào kênh thoại trước!', ephemeral: true });
            
            await interaction.deferReply();

            let player = client.manager.players.get(interaction.guild.id);
            if (!player) {
                player = await client.manager.createPlayer({
                    guildId: interaction.guild.id,
                    textId: interaction.channel.id,
                    voiceId: channel.id,
                    volume: 100,
                    deaf: true
                });
            }

            // Xử lý tìm kiếm nhạc an toàn
            try {
                const result = await client.manager.search(query, { requester: interaction.user });
                
                if (!result || !result.tracks || !result.tracks.length) {
                    return interaction.editReply('❌ Không tìm thấy bài hát. Bạn thử link khác xem sao!');
                }

                if (result.type === 'PLAYLIST') {
                    for (const track of result.tracks) player.queue.add(track);
                    interaction.editReply(`🟢 Đã nạp Playlist **${result.playlistName}** gồm **${result.tracks.length}** bài hát!`);
                } else {
                    player.queue.add(result.tracks[0]);
                    interaction.editReply(`🟢 Đã thêm: **${result.tracks[0].title}**`);
                }

                if (!player.playing && !player.paused) player.play();

            } catch (searchErr) {
                console.error("Lỗi khi cào nhạc:", searchErr);
                interaction.editReply('❌ Máy chủ âm thanh Lavalink hiện đang phản hồi chậm. Vui lòng thử lại sau!');
            }
        }

        if (interaction.commandName === 'skip') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player || !player.playing) return interaction.reply('❌ Không có bài nào để bỏ qua.');
            player.skip();
            interaction.reply('⏭️ Đã bỏ qua!');
        }

        if (interaction.commandName === 'stop') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player) return interaction.reply('❌ Bot không ở trong kênh thoại.');
            player.destroy();
            interaction.reply('🛑 Đã dừng phát và rời kênh.');
        }

    } catch (globalErr) {
        console.error("Lỗi xử lý hệ thống:", globalErr);
        if (interaction.deferred) {
            interaction.editReply("❌ Đã xảy ra lỗi nội bộ hệ thống, nhưng bot vẫn an toàn!");
        } else {
            interaction.reply({ content: "❌ Đã xảy ra lỗi nội bộ hệ thống.", ephemeral: true });
        }
    }
});

client.login(process.env.DISCORD_TOKEN);