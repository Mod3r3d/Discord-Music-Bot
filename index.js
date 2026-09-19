require('dotenv').config();
const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const { Kazagumo } = require('kazagumo');
const KazagumoSpotify = require('kazagumo-spotify');
const { Connectors } = require('shoukaku');
const express = require('express');

// ==========================================
// 1. HỆ THỐNG ANTI-CRASH (BẢO VỆ BOT)
// ==========================================
process.on('unhandledRejection', (reason) => console.error('⚠️ [ANTI-CRASH] Promise:', reason));
process.on('uncaughtException', (error) => console.error('⚠️ [ANTI-CRASH] System:', error));
process.on('uncaughtExceptionMonitor', (error) => console.error('⚠️ [ANTI-CRASH] Monitor:', error));

const app = express();
app.get('/', (req, res) => res.send('Bot Node.js đang hoạt động với đầy đủ tính năng!'));
app.listen(process.env.PORT || 8080, '0.0.0.0');

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates, GatewayIntentBits.GuildMessages]
});

// ==========================================
// 2. KẾT NỐI LAVALINK & PLUGIN SPOTIFY
// ==========================================
const Nodes = [{
    name: 'Ajie_V4_SSL',
    url: 'lava-v4.ajieblogs.eu.org:443',
    auth: 'https://dsc.gg/ajidevserver',
    secure: true
}];

client.manager = new Kazagumo({
    defaultSearchEngine: "youtube",
    plugins: [
        new KazagumoSpotify({
            clientId: process.env.SPOTIFY_CLIENT_ID,
            clientSecret: process.env.SPOTIFY_CLIENT_SECRET,
            playlistPageLimit: 10, // Lấy tối đa 10 trang (1000 bài hát) để phá vỡ giới hạn 100
            albumPageLimit: 2,
            searchLimit: 10,
            searchMarket: 'VN',
        })
    ],
    send: (guildId, payload) => {
        const guild = client.guilds.cache.get(guildId);
        if (guild) guild.shard.send(payload);
    }
}, new Connectors.DiscordJS(client), Nodes);

// HIỂN THỊ THÔNG BÁO KHI BẮT ĐẦU PHÁT BÀI MỚI
client.manager.on('playerStart', (player, track) => {
    const channel = client.channels.cache.get(player.textId);
    if (channel) channel.send(`🎶 **Đang phát:** \`${track.title}\` - *${track.author}*`);
});

client.manager.shoukaku.on('ready', (name) => console.log(`✅ Lavalink Node: ${name} đã kết nối!`));
client.manager.shoukaku.on('error', (name, error) => console.error(`❌ Lỗi Lavalink:`));
client.manager.on('playerEmpty', player => player.destroy());

// ==========================================
// 3. ĐĂNG KÝ DANH SÁCH LỆNH SLASH
// ==========================================
const commands = [
    { name: 'play', description: 'Phát nhạc (Hỗ trợ Youtube, Spotify vô hạn bài)', options: [{ name: 'query', type: 3, description: 'Tên bài hoặc URL', required: true }] },
    { name: 'skip', description: 'Bỏ qua bài hiện tại' },
    { name: 'skipto', description: 'Nhảy đến vị trí bài hát trong hàng đợi', options: [{ name: 'vitri', type: 4, description: 'Nhập số (VD: 5)', required: true }] },
    { name: 'queue', description: 'Xem danh sách chờ' },
    { name: 'pause', description: 'Tạm dừng nhạc' },
    { name: 'resume', description: 'Tiếp tục phát nhạc' },
    { name: 'stop', description: 'Dừng nhạc và thoát' }
];

client.once('ready', async () => {
    console.log(`🎉 Bot đã online: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(Routes.applicationCommands(client.user.id), { body: commands });
        console.log('✅ Đã đồng bộ toàn bộ lệnh Slash!');
    } catch (e) {
        console.error('❌ Lỗi đồng bộ lệnh:', e);
    }
});

// ==========================================
// 4. XỬ LÝ LỆNH TỪ NGƯỜI DÙNG
// ==========================================
client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    try {
        if (interaction.commandName === 'play') {
            const query = interaction.options.getString('query');
            const { channel } = interaction.member.voice;
            if (!channel) return interaction.reply({ content: '❌ Bạn cần vào kênh thoại trước!', ephemeral: true });
            
            await interaction.deferReply();

            let player = client.manager.players.get(interaction.guild.id) || await client.manager.createPlayer({
                guildId: interaction.guild.id, textId: interaction.channel.id, voiceId: channel.id, volume: 100, deaf: true
            });

            const result = await client.manager.search(query, { requester: interaction.user });
            if (!result || !result.tracks.length) return interaction.editReply('❌ Không tìm thấy bài hát!');

            if (result.type === 'PLAYLIST') {
                for (const track of result.tracks) player.queue.add(track);
                interaction.editReply(`🟢 Đã nạp Playlist **${result.playlistName}** gồm **${result.tracks.length}** bài hát!`);
            } else {
                player.queue.add(result.tracks[0]);
                interaction.editReply(`🟢 Đã thêm: **${result.tracks[0].title}**`);
            }
            if (!player.playing && !player.paused) player.play();
        }

        if (interaction.commandName === 'skip') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player || !player.playing) return interaction.reply('❌ Không có bài nào để bỏ qua.');
            player.skip();
            interaction.reply('⏭️ Đã bỏ qua bài hiện tại!');
        }

        if (interaction.commandName === 'skipto') {
            const position = interaction.options.getInteger('vitri');
            const player = client.manager.players.get(interaction.guild.id);
            if (!player || !player.playing) return interaction.reply('❌ Không có bài nào đang phát.');
            if (position < 1 || position > player.queue.length) return interaction.reply(`❌ Vị trí không hợp lệ. Hàng đợi hiện có ${player.queue.length} bài.`);
            
            // Xóa các bài từ vị trí 0 đến vị trí (position - 1)
            player.queue.splice(0, position - 1);
            player.skip();
            interaction.reply(`⏭️ Đã nhảy thẳng đến bài số **${position}**!`);
        }

        if (interaction.commandName === 'queue') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player || !player.queue.length) return interaction.reply('📭 Hàng đợi đang trống.');
            
            const queueString = player.queue.slice(0, 10).map((track, i) => `${i + 1}. ${track.title}`).join('\n');
            const remaining = player.queue.length > 10 ? `\n*... và ${player.queue.length - 10} bài khác*` : '';
            interaction.reply(`📜 **Danh sách chờ (${player.queue.length} bài):**\n${queueString}${remaining}`);
        }

        if (interaction.commandName === 'pause') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player || !player.playing) return interaction.reply('❌ Không có bài nào đang phát.');
            if (player.paused) return interaction.reply('⚠️ Nhạc đã được tạm dừng từ trước rồi.');
            
            player.pause(true);
            interaction.reply('⏸️ Đã tạm dừng nhạc!');
        }

        if (interaction.commandName === 'resume') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player) return interaction.reply('❌ Không có kết nối âm thanh.');
            if (!player.paused) return interaction.reply('⚠️ Nhạc vẫn đang phát bình thường.');
            
            player.pause(false);
            interaction.reply('▶️ Đã tiếp tục phát nhạc!');
        }

        if (interaction.commandName === 'stop') {
            const player = client.manager.players.get(interaction.guild.id);
            if (!player) return interaction.reply('❌ Bot không ở trong kênh thoại.');
            player.destroy();
            interaction.reply('🛑 Đã dừng nhạc và xóa toàn bộ hàng đợi.');
        }

    } catch (globalErr) {
        console.error("Lỗi:", globalErr);
        if (interaction.deferred) {
            interaction.editReply("❌ Có lỗi hệ thống xảy ra hoặc máy chủ đang tải!");
        } else {
            interaction.reply({ content: "❌ Có lỗi hệ thống xảy ra!", ephemeral: true });
        }
    }
});

client.login(process.env.DISCORD_TOKEN);