/**
 * /resume — Tiếp tục phát nhạc.
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');

const definition = {
    name: 'resume',
    description: 'Tiếp tục phát nhạc'
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    playerService.resume(playerCheck.player);
    await interaction.reply('▶️ Đã tiếp tục phát nhạc!');
}

module.exports = { definition, execute };
