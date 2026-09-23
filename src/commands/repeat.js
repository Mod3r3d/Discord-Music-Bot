/**
 * /repeat — Chế độ lặp (off / track / queue).
 */

const { checkPlayer, checkSameVoiceChannel } = require('../utils/permissions');
const { getState } = require('../services/player/PlayerState');

const REPEAT_EMOJIS = { off: '➡️', track: '🔂', queue: '🔁' };
const REPEAT_LABELS = { off: 'Tắt', track: 'Lặp bài hiện tại', queue: 'Lặp danh sách' };

const definition = {
    name: 'repeat',
    description: 'Đổi chế độ lặp',
    options: [{
        name: 'mode',
        type: 3, // STRING
        description: 'Chế độ lặp',
        required: false,
        choices: [
            { name: '➡️ Tắt lặp', value: 'off' },
            { name: '🔂 Lặp bài hiện tại', value: 'track' },
            { name: '🔁 Lặp danh sách', value: 'queue' }
        ]
    }]
};

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) return interaction.reply({ content: playerCheck.error, ephemeral: true });

    const voiceCheck = checkSameVoiceChannel(interaction.member, playerCheck.player);
    if (!voiceCheck.ok) return interaction.reply({ content: voiceCheck.error, ephemeral: true });

    const state = getState(interaction.guild.id);
    const modeArg = interaction.options.getString('mode');

    let newMode;
    if (modeArg) {
        state.setRepeatMode(modeArg);
        newMode = modeArg;
    } else {
        // Toggle vòng: off → track → queue → off
        newMode = state.cycleRepeatMode();
    }

    const emoji = REPEAT_EMOJIS[newMode] || '➡️';
    const label = REPEAT_LABELS[newMode] || 'Tắt';

    await interaction.reply(`${emoji} Chế độ lặp: **${label}**`);
}

module.exports = { definition, execute };
