/**
 * PlayerService — Điều phối phát nhạc, tích hợp Generation Guard.
 *
 * Là lớp trung gian giữa commands/buttons và Kazagumo Player.
 * Mọi hành động phát nhạc đều đi qua service này.
 */

const { getState, removeState } = require('./PlayerState');
const queueService = require('../queue/QueueService');
const NowPlayingUI = require('../ui/NowPlayingUI');

class PlayerService {
    /**
     * @param {import('discord.js').Client} client - Discord client
     * @param {import('kazagumo').Kazagumo} manager - Kazagumo manager
     */
    constructor(client, manager) {
        this.client = client;
        this.manager = manager;
    }

    /**
     * Lấy hoặc tạo player cho guild.
     * @param {object} opts - { guildId, textId, voiceId }
     * @returns {Promise<object>} Kazagumo player
     */
    async getOrCreatePlayer({ guildId, textId, voiceId }) {
        let player = this.manager.players.get(guildId);
        // Nếu player đã bị destroy hoặc mất kết nối voice, dọn dẹp để tạo mới
        if (player && (player.state === 'DESTROYED' || player.state === 'DESTROYING' || !player.voiceId)) {
            try { await player.destroy(); } catch (_) {}
            this.manager.players.delete(guildId);
            player = null;
        }

        if (!player) {
            player = await this.manager.createPlayer({
                guildId,
                textId,
                voiceId,
                volume: 130, // Mặc định 130% để to và rõ hơn
                deaf: true
            });
        } else {
            if (textId && player.textId !== textId) player.setTextChannel(textId);
            if (voiceId && player.voiceId !== voiceId) player.setVoiceChannel(voiceId);
        }
        return player;
    }

    /**
     * Tìm kiếm bài hát kèm cơ chế Fallback thông minh.
     * @param {string} query - Từ khóa hoặc URL
     * @param {object} requester - Discord user
     * @returns {Promise<object>} Kết quả tìm kiếm Kazagumo
     */
    async search(query, requester) {
        console.log(`🔍 [Search] Bắt đầu tìm kiếm: "${query}"`);
        let result = null;

        const withTimeout = (promise, ms, desc) => {
            let timer;
            const timeout = new Promise((_, reject) => {
                timer = setTimeout(() => reject(new Error(`Quá thời gian (${ms / 1000}s): ${desc}`)), ms);
            });
            return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
        };

        try {
            result = await withTimeout(this.manager.search(query, { requester }), 35000, 'Kazagumo search');
        } catch (err) {
            console.error(`⚠️ [Search] Kazagumo search error:`, err.message);
        }

        // Fallback 1: Nếu plugin (như Spotify) trả về rỗng hoặc lỗi token/private playlist,
        // thử tìm kiếm trực tiếp qua Lavalink Node (Kazagumo._search)
        if (!result || !result.tracks || result.tracks.length === 0) {
            console.log(`⚠️ [Search] Không có kết quả từ plugin, thử fallback qua Lavalink...`);
            try {
                if (typeof this.manager._search === 'function') {
                    result = await withTimeout(this.manager._search(query, { requester }), 15000, 'Fallback _search');
                }
            } catch (fallbackErr) {
                console.error(`❌ [Search] Fallback _search error:`, fallbackErr.message);
            }
        }

        // Fallback 2: Nếu là từ khóa tìm kiếm (không phải URL) và vẫn chưa thấy bài nào,
        // thử ép kiểu tìm kiếm YouTube trực tiếp
        if ((!result || !result.tracks || result.tracks.length === 0) && !/^https?:\/\//.test(query)) {
            console.log(`⚠️ [Search] Thử tìm kiếm với tiền tố ytsearch: "${query}"...`);
            try {
                result = await withTimeout(this.manager.search(`ytsearch:${query}`, { requester }), 15000, 'ytsearch');
            } catch (ytErr) {
                console.error(`❌ [Search] YouTube prefix error:`, ytErr.message);
            }
        }

        console.log(`✅ [Search] Kết quả hoàn tất: Type=${result?.type || 'NONE'}, Số tracks=${result?.tracks?.length || 0}`);
        return result;
    }

    /**
     * Thêm track và phát nếu chưa phát gì.
     * @param {object} player - Kazagumo player
     * @param {object} track - Kazagumo track
     */
    async enqueueAndPlay(player, track) {
        queueService.add(player, track);
        console.log(`[PlayerService] enqueueAndPlay: playing=${player.playing}, current=${player.queue.current?.title}`);
        if (!player.playing) {
            try {
                await player.play();
            } catch (err) {
                console.error('[PlayerService] Lỗi khi gọi player.play():', err);
            }
        }
    }

    /**
     * Thêm nhiều tracks (playlist) và phát nếu chưa phát gì.
     * @param {object} player - Kazagumo player
     * @param {object[]} tracks - Mảng Kazagumo tracks
     */
    async enqueueMultipleAndPlay(player, tracks) {
        queueService.add(player, tracks);
        console.log(`[PlayerService] enqueueMultipleAndPlay: nạp ${tracks.length} bài. playing=${player.playing}, current=${player.queue.current?.title}`);
        if (!player.playing) {
            try {
                await player.play();
            } catch (err) {
                console.error('[PlayerService] Lỗi khi gọi player.play() (playlist):', err);
            }
        }
    }

    /**
     * Chèn bài lên đầu hàng đợi (Play Top).
     * @param {object} player - Kazagumo player
     * @param {object} track - Kazagumo track
     */
    enqueueTop(player, track) {
        queueService.addTop(player, track);
        if (!player.playing && !player.paused) {
            player.play();
        }
    }

    /**
     * Bỏ qua bài hiện tại, phát ngay bài mới (Play Skip).
     * Sử dụng generation guard để chống phát nhầm.
     * @param {object} player - Kazagumo player
     * @param {object} track - Kazagumo track
     */
    playSkip(player, track) {
        const state = getState(player.guildId);
        state.incrementGeneration();

        // Chèn bài mới lên đầu queue rồi skip bài hiện tại
        queueService.addTop(player, track);
        if (player.playing || player.paused) {
            player.skip();
        } else {
            player.play();
        }
    }

    /**
     * Bỏ qua bài hiện tại (Skip).
     * @param {object} player - Kazagumo player
     * @returns {boolean} true nếu thành công
     */
    skip(player) {
        const state = getState(player.guildId);
        state.incrementGeneration();

        if (!player.playing && !player.paused) return false;
        player.skip();
        return true;
    }

    /**
     * Nhảy đến vị trí bài hát trong queue (Skip To).
     * @param {object} player - Kazagumo player
     * @param {number} position - Vị trí bài hát (1-based, hiển thị cho user)
     * @returns {{ ok: boolean, error?: string }}
     */
    skipTo(player, position) {
        const state = getState(player.guildId);

        if (!player.playing && !player.paused) {
            return { ok: false, error: '❌ Không có bài nào đang phát.' };
        }
        if (position < 1 || position > player.queue.length) {
            return { ok: false, error: `❌ Vị trí không hợp lệ. Hàng đợi hiện có **${player.queue.length}** bài.` };
        }

        state.incrementGeneration();

        // Xóa (position - 1) bài trước vị trí đó
        player.queue.splice(0, position - 1);
        player.skip();
        return { ok: true };
    }

    /**
     * Tạm dừng phát nhạc.
     * @param {object} player
     */
    pause(player) {
        player.pause(true);
    }

    /**
     * Tiếp tục phát nhạc.
     * @param {object} player
     */
    resume(player) {
        player.pause(false);
    }

    async stop(player) {
        const state = getState(player.guildId);
        state.incrementGeneration();
        state.clearNowPlaying();
        player.queue.length = 0;
        player.queue.current = null;
        try {
            await player.destroy();
        } catch (_) {}
        this.manager.players.delete(player.guildId);
    }

    /**
     * Phát lại bài vừa nghe gần nhất từ lịch sử.
     * @param {object} player - Kazagumo player
     * @returns {{ ok: boolean, track?: object, error?: string }}
     */
    previous(player) {
        const state = getState(player.guildId);

        if (state.history.length === 0) {
            return { ok: false, error: '❌ Lịch sử trống, không có bài nào để phát lại.' };
        }

        const prevTrack = state.popFromHistory();
        state.incrementGeneration();

        // Chèn bài lịch sử lên đầu queue rồi skip bài hiện tại
        queueService.addTop(player, prevTrack.raw || prevTrack);
        if (player.playing || player.paused) {
            player.skip();
        } else {
            player.play();
        }

        return { ok: true, track: prevTrack };
    }

    /**
     * Xử lý sự kiện khi bài hát bắt đầu phát.
     * Ghi nhận, gửi Now Playing embed.
     * @param {object} player - Kazagumo player
     * @param {object} track - Track đang phát
     */
    async onTrackStart(player, track) {
        console.log(`🎵 [PlayerService] onTrackStart: "${track?.title}" trên guild ${player.guildId}, textId=${player.textId}`);
        const state = getState(player.guildId);
        state.clearNowPlaying();

        const channel = this.client.channels.cache.get(player.textId);
        if (!channel) {
            console.error(`❌ [PlayerService] Không tìm thấy text channel ${player.textId} để gửi Now Playing!`);
            return;
        }

        try {
            const { embed, components } = NowPlayingUI.create(player, track, state);
            const msg = await channel.send({ embeds: [embed], components });

            state.nowPlayingMessageId = msg.id;
            state.nowPlayingChannelId = channel.id;

            // Cập nhật thanh tiến trình mỗi 10 giây
            state.progressInterval = setInterval(async () => {
                try {
                    const currentTrack = player.queue.current || track;
                    if (!currentTrack || !state.nowPlayingMessageId) {
                        state.clearNowPlaying();
                        return;
                    }
                    if (player.paused) return; // Đang tạm dừng thì giữ nguyên UI

                    const updated = NowPlayingUI.create(player, currentTrack, state);
                    await msg.edit({ embeds: [updated.embed], components: updated.components }).catch(err => {
                        if (err && err.code === 10008) { // Tin nhắn đã bị người dùng xóa trên Discord
                            state.clearNowPlaying();
                        }
                    });
                } catch (err) {
                    console.error('[PlayerService] Lỗi cập nhật tiến trình Now Playing:', err.message);
                }
            }, 10_000);

        } catch (err) {
            console.error('[PlayerService] Lỗi gửi Now Playing:', err.message);
        }
    }

    /**
     * Xử lý sự kiện khi bài hát kết thúc.
     * Đưa bài vào history, xử lý repeat mode.
     * @param {object} player - Kazagumo player
     * @param {object} track - Track vừa phát xong
     */
    onTrackEnd(player, track) {
        const state = getState(player.guildId);
        state.clearNowPlaying();

        // Lưu vào lịch sử
        if (track) {
            state.addToHistory({
                title: track.title,
                author: track.author,
                uri: track.uri,
                duration: track.length || track.duration || 0,
                thumbnail: track.thumbnail,
                requesterId: track.requester ? track.requester.id : null,
                requesterName: track.requester ? (track.requester.globalName || track.requester.username) : 'Unknown',
                raw: track,
                source: track.sourceName || 'unknown'
            });
        }

        // Xử lý Repeat mode
        if (state.repeatMode === 'track' && track) {
            // Phát lại bài hiện tại
            queueService.addTop(player, track);
        } else if (state.repeatMode === 'queue' && track) {
            // Đẩy bài vừa phát xuống cuối queue
            queueService.add(player, track);
        }
    }

    /**
     * Xử lý khi player hết bài trong queue.
     * @param {object} player - Kazagumo player
     */
    onPlayerEmpty(player) {
        const state = getState(player.guildId);
        state.clearNowPlaying();
        // Tự hủy player sau khi hết bài
        player.destroy();
    }

    /**
     * Xử lý khi player bị hủy.
     * @param {string} guildId
     */
    onPlayerDestroy(guildId) {
        removeState(guildId);
    }
}

module.exports = PlayerService;
