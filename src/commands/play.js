/**
 * /play — Phát nhạc từ URL hoặc từ khóa tìm kiếm.
 */

const { checkVoiceChannel } = require('../utils/permissions');

/** Định nghĩa Slash Command */
const definition = {
    name: 'play',
    description: 'Phát nhạc từ YouTube, Spotify hoặc từ khóa',
    options: [{
        name: 'query',
        type: 3, // STRING
        description: 'Tên bài hát hoặc URL (YouTube, Spotify, SoundCloud...)',
        required: true
    }]
};

/**
 * Xử lý lệnh /play.
 * @param {import('discord.js').ChatInputCommandInteraction} interaction
 * @param {import('../services/player/PlayerService')} playerService
 */
async function execute(interaction, playerService) {
    const query = interaction.options.getString('query');
    console.log(`[play] Nhận lệnh từ ${interaction.user.tag} với query: "${query}"`);

    // Kiểm tra user có ở voice channel không
    const voiceCheck = checkVoiceChannel(interaction.member);
    if (!voiceCheck.ok) {
        return interaction.reply({ content: voiceCheck.error, ephemeral: true });
    }

    await interaction.deferReply();

    try {
        // Lấy hoặc tạo player
        const player = await playerService.getOrCreatePlayer({
            guildId: interaction.guild.id,
            textId: interaction.channel.id,
            voiceId: voiceCheck.channel.id
        });

        // Tìm kiếm
        const result = await playerService.search(query, interaction.user);
        if (!result || !result.tracks || !result.tracks.length) {
            return interaction.editReply('❌ Không tìm thấy bài hát hoặc danh sách phát trống!');
        }

        // Xử lý kết quả
        if (result.type === 'PLAYLIST') {
            playerService.enqueueMultipleAndPlay(player, result.tracks);
            await interaction.editReply(
                `🟢 Đã nạp Playlist **${result.playlistName || 'Danh sách phát'}** gồm **${result.tracks.length}** bài hát!`
            );
        } else {
            const track = result.tracks[0];
            playerService.enqueueAndPlay(player, track);
            await interaction.editReply(`🟢 Đã thêm: **${track.title}**`);
        }
    } catch (err) {
        console.error('[play] Error:', err);
        if (interaction.deferred) {
            await interaction.editReply(`❌ Lỗi khi tải nhạc: ${err.message || err}`);
        } else {
            await interaction.reply({ content: `❌ Lỗi: ${err.message || err}`, ephemeral: true });
        }
    }
}

module.exports = { definition, execute };
