/**
 * /skip & /skipto — Bỏ qua bài hiện tại hoặc nhảy đến vị trí trong queue.
 */

const { checkPlayer, checkPlaying, checkSameVoiceChannel } = require('../utils/permissions');

const definitions = [
    {
        name: 'skip',
        description: 'Bỏ qua bài hiện tại'
    },
    {
        name: 'skipto',
        description: 'Nhảy đến vị trí bài hát trong hàng đợi',
        options: [{
            name: 'index',
            type: 4, // INTEGER
            description: 'Nhập số thứ tự bài hát (VD: 5)',
            required: true
        }]
    }
];

async function executeSkip(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const playingCheck = checkPlaying(playerCheck.player);
    if (!playingCheck.ok) return interaction.reply({ content: '❌ Không có bài nào để bỏ qua.', ephemeral: true });

    playerService.skip(playerCheck.player);
    await interaction.reply('⏭️ Đã bỏ qua bài hiện tại!');
}

async function executeSkipTo(interaction, playerService) {
    const position = interaction.options.getInteger('index');

    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const result = playerService.skipTo(playerCheck.player, position);
    if (!result.ok) return interaction.reply({ content: result.error, ephemeral: true });

    await interaction.reply(`⏭️ Đã nhảy thẳng đến bài số **${position}**!`);
}

module.exports = { definitions, executeSkip, executeSkipTo };
