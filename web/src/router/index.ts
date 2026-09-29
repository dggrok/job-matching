import { createRouter, createWebHashHistory } from 'vue-router'

// 使用 hash 路由,静态托管(无需服务端重写规则)也能直接访问。
export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/results' },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { title: '我的条件' } },
    { path: '/results', name: 'results', component: () => import('@/views/ResultsView.vue'), meta: { title: '匹配结果' } },
    { path: '/favorites', name: 'favorites', component: () => import('@/views/FavoritesView.vue'), meta: { title: '收藏与对比' } },
    { path: '/about', name: 'about', component: () => import('@/views/AboutView.vue'), meta: { title: '数据说明' } },
  ],
})
