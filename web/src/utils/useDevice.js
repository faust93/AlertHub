import { ref, onMounted, onUnmounted } from 'vue';

export function useDevice(breakpoint = 768) {
  const isMobile = ref(false);

  function update() {
    isMobile.value = window.innerWidth <= breakpoint;
  }

  onMounted(() => {
    update();
    window.addEventListener('resize', update);
  });

  onUnmounted(() => {
    window.removeEventListener('resize', update);
  });

  return { isMobile };
}
