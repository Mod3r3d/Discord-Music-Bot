/**
 * /nowplaying & /np — Xem thông tin bài hát đang phát.
 */

const { checkPlayer } = require('../utils/permissions');
const { getState } = require('../services/player/PlayerState');
const NowPlayingUI = require('../services/ui/NowPlayingUI');

const definitions = [
    {
        name: 'nowplaying',
        description: 'Xem thông tin và thanh điều khiển bài hát đang phát'
    },
    {
        name: 'np',
        description: 'Xem thông tin và thanh điều khiển bài hát đang phát'
    }
];

async function execute(interaction, playerService) {
    const playerCheck = checkPlayer(playerService.manager, interaction.guild.id);
    if (!playerCheck.ok) {
        return interaction.reply({ content: '❌ Không có bài hát nào đang phát!', ephemeral: true });
    }

    const player = playerCheck.player;
    const currentTrack = player.queue.current;
    if (!currentTrack) {
        return interaction.reply({ content: '❌ Không có bài hát nào đang phát!', ephemeral: true });
    }

    const state = getState(interaction.guild.id);
    const { embed, components } = NowPlayingUI.create(player, currentTrack, state);
    await interaction.reply({ embeds: [embed], components });
}

module.exports = { definitions, execute };
