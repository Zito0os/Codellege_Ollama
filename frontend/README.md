# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.



IDEA PRINCIPAL
--------------
¿QUE COMERE HOY?

Pagina en donde en base a parametros los cuales seran ingredientes que se ecnontraran en el refrigerados estos aun hayq ue ver si se especificaran o no , con esto tendria que darte una receta aleatoria para poder comer

FLUJO
-------------

-El usuario entra a la pagina y describe los ingredientes que tiene a disposicion(meter modelo de vison a futuro para automatizalo con una imagen)
-El cliente tendra que especificar las herramientas con las que cuenta (estufa microondas, etc)
-El usuario medainte un formulario especificara quie tipo de comida quiere
    -Este sera el tipo de comida (oriental,francesa,algo rapido etc) si el usuario no especifica cual es su preferencia el sistema manda aleatorio y la opcion rapida
-El prompt reunira todas las especificaciones dadas
-En base a eso generara una respuesta la cual seria una receta que se ajuste a las especificaciones del cliente 
-El maximo de recetas que se pueden pedir son 4 
-El sistema debera de entregar en total 4 respuestas si el usuario especifica que quiere ver la opcion de 2 tipos de comida tendra que manadar 2 de cada una para completar 4 


-Hacer onboarding
-Al inicio de la sesion tendras que especificar que herraminetas tienes y en base a eso ya no tener que poner en el prompt cada vez las herramientas que tienes