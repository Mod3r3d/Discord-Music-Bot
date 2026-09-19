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
// 3. CỤM MÁY CHỦ LAVALINK V4 MỚI NHẤT
// ==========================================
const Nodes = [
    {
        name: 'Oops_V4',
        url: 'lavalink.oops.wtf:2000',
        auth: 'www.freelavalink.mp3',
        secure: false
    },
    {
        name: 'Krypton_V4',
        url: 'node1.krypton.ninja:3128',
        auth: 'krypton',
        secure: false
    },
    {
        name: 'Lava_Link_Default',
        url: 'lava.link:88',
        auth: 'youshallnotpass',
        secure: false
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
client.manager.shoukaku.on('error', (name, error) => console.error(`❌ Lỗi Lavalink (${name}): Có thể node đang offline.`));
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

    if (interaction.commandName === 'play') {
        const query = interaction.options.getString('query');
        const { channel } = interaction.member.voice;
        
        if (!channel) return interaction.reply({ content: '❌ Bạn cần vào kênh thoại trước!', ephemeral: true });
        
        // Trả lời tạm để Discord không báo lỗi timeout "đang suy nghĩ..."
        await interaction.deferReply();

        try {
            // Đưa việc tạo Player vào vùng an toàn, phòng khi mọi node đều sập
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

            // Xử lý tìm kiếm nhạc
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

        } catch (err) {
            console.error("Lỗi khi kết nối hoặc cào nhạc:", err);
            interaction.editReply('❌ Các máy chủ âm thanh hiện đang quá tải. Vui lòng đợi một lát rồi thử lại!');
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
});

client.login(process.env.DISCORD_TOKEN);