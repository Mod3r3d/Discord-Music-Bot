require('dotenv').config();
const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const { Kazagumo } = require('kazagumo');
const { Connectors } = require('shoukaku');
const express = require('express');

// Khởi tạo Web Server để Render không tắt bot
const app = express();
app.get('/', (req, res) => res.send('Bot Node.js đang chạy tốt!'));
const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`🌐 Web server đang chạy trên port ${PORT}`));

// Khởi tạo Discord Bot
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
    ]
});

// Kết nối tới máy chủ âm thanh Lavalink
const Nodes = [{
    name: 'Main_Node',
    url: process.env.LAVALINK_URI || 'lava-v3.ajieblogs.eu.org:3132',
    auth: process.env.LAVALINK_PASSWORD || 'https://dsc.gg/ajidevserver',
    secure: false
}];

client.manager = new Kazagumo({
    defaultSearchEngine: "youtube",
    send: (guildId, payload) => {
        const guild = client.guilds.cache.get(guildId);
        if (guild) guild.shard.send(payload);
    }
}, new Connectors.DiscordJS(client), Nodes);

client.manager.shoukaku.on('ready', (name) => console.log(`✅ Đã kết nối với máy chủ âm thanh: ${name}`));
client.manager.shoukaku.on('error', (name, error) => console.error(`❌ Lỗi máy chủ âm thanh (${name}):`, error));

client.manager.on('playerEmpty', player => player.destroy());

// Đăng ký lệnh Slash
const commands = [
    {
        name: 'play',
        description: 'Phát nhạc từ YouTube, Spotify, SoundCloud...',
        options: [{ name: 'query', type: 3, description: 'Tên bài hát hoặc link Playlist', required: true }]
    },
    { name: 'skip', description: 'Bỏ qua bài hiện tại' },
    { name: 'stop', description: 'Dừng nhạc và thoát' }
];

client.once('ready', async () => {
    console.log(`🎉 Bot đã online: ${client.user.tag}`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    try {
        await rest.put(Routes.applicationCommands(client.user.id), { body: commands });
        console.log('✅ Đã đồng bộ lệnh Slash lên Discord!');
    } catch (error) {
        console.error('❌ Lỗi đồng bộ lệnh:', error);
    }
});

// Xử lý khi người dùng gõ lệnh
client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

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

        const result = await client.manager.search(query, { requester: interaction.user });
        if (!result.tracks.length) return interaction.editReply('❌ Không tìm thấy bài hát!');

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