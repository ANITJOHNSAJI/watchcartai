// let slideIndex = 0;

// function showSlide(index) {
//     const slides = document.querySelectorAll('.carousel-item');
//     if (index >= slides.length) {
//         slideIndex = 0;
//     } else if (index < 0) {
//         slideIndex = slides.length - 1;
//     } else {
//         slideIndex = index;
//     }
//     const carouselSlide = document.querySelector('.carousel-slide');
//     carouselSlide.style.transform = `translateX(${-slideIndex * 100}%)`;
// }

// function moveSlide(step) {
//     showSlide(slideIndex + step);
// }

// showSlide(slideIndex);