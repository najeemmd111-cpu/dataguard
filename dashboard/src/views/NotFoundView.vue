<template>
  <div class="page">
    <h1 class="page-title">This page doesn’t exist</h1>
    <p class="lede">
      Check the address, or go back to
      <RouterLink :to="{ name: 'overview' }">all contracts</RouterLink>.
    </p>
  </div>
</template>
