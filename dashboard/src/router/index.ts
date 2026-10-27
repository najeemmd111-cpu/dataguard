import { createRouter, createWebHistory } from 'vue-router'

import OverviewView from '../views/OverviewView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'overview', component: OverviewView, meta: { title: 'Overview' } },
    {
      path: '/datasets/:name',
      name: 'dataset',
      component: () => import('../views/DatasetView.vue'),
      props: true,
      meta: { title: 'Dataset' },
    },
    {
      path: '/runs',
      name: 'runs',
      component: () => import('../views/RunsView.vue'),
      meta: { title: 'Run history' },
    },
    {
      path: '/audit',
      name: 'audit',
      component: () => import('../views/AuditView.vue'),
      meta: { title: 'AI access log' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
      meta: { title: 'Not found' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const name = to.name === 'dataset' ? String(to.params.name) : (to.meta.title as string)
  document.title = `${name} — DataGuard`
})

export default router
