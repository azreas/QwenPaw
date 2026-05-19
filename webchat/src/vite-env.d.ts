declare module "*.module.less" {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module "*.module.css" {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module "*.less" {
  const content: string;
  export default content;
}

declare module "*.css" {
  const content: string;
  export default content;
}
