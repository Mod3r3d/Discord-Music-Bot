/**
 * Cấu hình danh sách Lavalink Nodes & fallback.
 * Đọc từ biến môi trường hoặc dùng default.
 */

const Nodes = [
    {
        name: 'Main_Node',
        url: process.env.LAVALINK_HOST || 'lavalink.darrennathanael.com:443',
        auth: process.env.LAVALINK_AUTH || 'youshallnotpass',
        secure: true
    },
    {
        name: 'Backup_Node',
        url: process.env.LAVALINK_HOST_BACKUP || 'lava-v4.ajieblogs.eu.org:443',
        auth: process.env.LAVALINK_AUTH_BACKUP || 'https://dsc.gg/ajidevserver',
        secure: true
    }
];

module.exports = { Nodes };
